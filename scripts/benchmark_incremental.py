import os
import shutil
import time
import sys
from collections import defaultdict

# Add project root to python path so backend/core/services can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.analysis_registry import AnalysisRegistry
from core.build_pipeline import BuildPipeline
from services.symbol_service import SymbolService
from services.architecture_service import ArchitectureService
from services.call_graph_service import CallGraphService
from services.api_surface_service import APISurfaceService
from backend.dependencies import snapshot_store, analysis_cache

def create_mock_repo(repo_dir, num_files=50):
    os.makedirs(repo_dir, exist_ok=True)
    for i in range(1, num_files + 1):
        content = f"""# Mock file {i} for benchmarking
def function_{i}(x):
    return x + {i}

class Class_{i}:
    def method_{i}(self):
        return function_{i}(10)
"""
        with open(os.path.join(repo_dir, f"file_{i}.py"), "w") as f:
            f.write(content)

def modify_files(repo_dir, file_indices):
    for i in file_indices:
        content = f"""# Mock file {i} modified
def function_{i}(x):
    # Added comment or change
    return x + {i} + 100

class Class_{i}:
    def method_{i}(self):
        return function_{i}(20)
"""
        with open(os.path.join(repo_dir, f"file_{i}.py"), "w") as f:
            f.write(content)

def main():
    repo_name = "benchmark/repo"
    repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "benchmark_temp_repo"))
    
    # Setup custom registry and pipeline
    benchmark_registry = AnalysisRegistry()
    benchmark_registry.register("Symbol Index", SymbolService, dependencies=[], outputs=["symbols"])
    benchmark_registry.register("Dependency Graph", ArchitectureService, dependencies=["Symbol Index"], outputs=["graphs/dependency"])
    benchmark_registry.register("Call Graph", CallGraphService, dependencies=["Symbol Index", "Dependency Graph"], outputs=["graphs/call", "call_graphs"])
    benchmark_registry.register("API Surface", APISurfaceService, dependencies=["Symbol Index", "Dependency Graph"], outputs=["api_surface"])
    
    pipeline = BuildPipeline(benchmark_registry)
    
    def run_build(max_workers: int, force_rebuild=False):
        # Track CPU time
        cpu_start = time.process_time()
        start_time = time.time()
        
        events = list(pipeline.build(repo_name, repo_path=repo_dir, force_rebuild=force_rebuild, max_workers=max_workers))
        
        wall_duration = (time.time() - start_time) * 1000
        cpu_duration = (time.process_time() - cpu_start) * 1000
        
        node_durations = {}
        tasks_executed = 0
        tasks_skipped = 0
        
        for e in events:
            if e.get("event") == "ERROR":
                print(f"Error executing build: {e.get('message')}")
                return None
            elif e.get("event") == "TASK_STARTED":
                tasks_executed += 1
            elif e.get("event") == "TASK_SKIPPED":
                tasks_skipped += 1
            elif e.get("event") == "BUILD TIME":
                node_durations[e["node"]] = e["duration_ms"]
                
        return {
            "wall_ms": wall_duration,
            "cpu_ms": cpu_duration,
            "node_durations": node_durations,
            "executed": tasks_executed,
            "skipped": tasks_skipped,
        }

    def clear_repo_snapshots():
        try:
            snapshot_store.delete(repo_name, "build_manifest")
            snapshot_store.delete(repo_name, "symbols")
            snapshot_store.delete(repo_name, "graphs/dependency")
            snapshot_store.delete(repo_name, "graphs/call")
            snapshot_store.delete(repo_name, "call_graphs")
            snapshot_store.delete(repo_name, "api_surface")
            analysis_cache.clear()
        except Exception:
            pass

    # Ensure clean state
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    clear_repo_snapshots()
        
    try:
        # --- Warmup Run ---
        print("Warming up parser libraries and cache...")
        create_mock_repo(repo_dir, 10)
        run_build(max_workers=1)
        modify_files(repo_dir, [1])
        run_build(max_workers=2)
        shutil.rmtree(repo_dir)
        clear_repo_snapshots()
        
        num_runs = 3
        # Results structure: mode (sequential/parallel) -> scenario -> run metrics
        metrics = {
            "sequential": defaultdict(list),
            "parallel": defaultdict(list)
        }
        
        print(f"\nRunning {num_runs} iterations of sequential (1 worker) vs parallel (4 workers) builds...")
        
        scenarios = [
            ("Full Build", lambda dir: None), # No modifications, runs on fresh repo
            ("No-change Rebuild", lambda dir: None), # Second run, nothing modified
            ("Single-file Change", lambda dir: modify_files(dir, [1])),
            ("5-file Change", lambda dir: modify_files(dir, [2, 3, 4, 5, 6])),
            ("50-file Change (All)", lambda dir: modify_files(dir, list(range(1, 51)))),
        ]
        
        for run in range(1, num_runs + 1):
            print(f"Iteration {run}/{num_runs}...")
            
            # --- Test Sequential Mode ---
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)
            clear_repo_snapshots()
            create_mock_repo(repo_dir, 50)
            
            for idx, (name, mod_fn) in enumerate(scenarios):
                if idx > 0:
                    mod_fn(repo_dir)
                res = run_build(max_workers=1)
                if res:
                    metrics["sequential"][name].append(res)
                    
            # --- Test Parallel Mode ---
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)
            clear_repo_snapshots()
            create_mock_repo(repo_dir, 50)
            
            for idx, (name, mod_fn) in enumerate(scenarios):
                if idx > 0:
                    mod_fn(repo_dir)
                res = run_build(max_workers=4)
                if res:
                    metrics["parallel"][name].append(res)

        # Compute Averages
        avg_metrics = defaultdict(dict)
        for mode in ["sequential", "parallel"]:
            for name, _ in scenarios:
                run_list = metrics[mode][name]
                if not run_list:
                    continue
                
                avg_wall = sum(r["wall_ms"] for r in run_list) / len(run_list)
                avg_cpu = sum(r["cpu_ms"] for r in run_list) / len(run_list)
                avg_exec = sum(r["executed"] for r in run_list) / len(run_list)
                avg_skip = sum(r["skipped"] for r in run_list) / len(run_list)
                
                node_avg = defaultdict(float)
                for r in run_list:
                    for n, d in r["node_durations"].items():
                        node_avg[n] += d
                for n in node_avg:
                    node_avg[n] /= len(run_list)
                    
                avg_metrics[mode][name] = {
                    "wall": avg_wall,
                    "cpu": avg_cpu,
                    "executed": avg_exec,
                    "skipped": avg_skip,
                    "node_durations": dict(node_avg)
                }

        # Print detailed report
        report = []
        report.append("# Concurrency Performance Benchmark Report")
        report.append("\n## Average Scenario Performance Summary\n")
        report.append("| Scenario | Sequential Wall-clock (ms) | Parallel Wall-clock (ms) | Speedup Factor | CPU Time (ms) | Executed Tasks | Skipped Tasks | Cache Hit Rate |")
        report.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        
        for name, _ in scenarios:
            seq = avg_metrics["sequential"][name]
            par = avg_metrics["parallel"][name]
            
            speedup = seq["wall"] / max(par["wall"], 0.001)
            total_tasks = seq["executed"] + seq["skipped"]
            hit_rate = (seq["skipped"] / total_tasks) * 100 if total_tasks > 0 else 0.0
            
            report.append(
                f"| **{name}** | {seq['wall']:.2f} ms | {par['wall']:.2f} ms | {speedup:.2f}x | {par['cpu']:.2f} ms | {par['executed']:.1f} | {par['skipped']:.1f} | {hit_rate:.1f}% |"
            )
            
        report.append("\n## Concurrency Utilization Metrics\n")
        report.append("| Scenario | Parallel Duration (ms) | Total Task Time (ms) | Worker Utilization | Parallel Efficiency |")
        report.append("| --- | --- | --- | --- | --- |")
        
        for name, _ in scenarios:
            seq = avg_metrics["sequential"][name]
            par = avg_metrics["parallel"][name]
            
            # Sum of task durations inside parallel threads
            total_task_time = sum(par["node_durations"].values())
            # Utilization = total task time / (wall clock time * workers)
            utilization = total_task_time / (par["wall"] * 4) if par["wall"] > 0 else 0.0
            # Efficiency = seq total task time / (par total time * workers)
            efficiency = seq["wall"] / (par["wall"] * 4) if par["wall"] > 0 else 0.0
            
            report.append(
                f"| **{name}** | {par['wall']:.2f} ms | {total_task_time:.2f} ms | {utilization:.2%} | {efficiency:.2%} |"
            )
            
        report_text = "\n".join(report)
        print("\n=== BENCHMARK REPORT ===")
        print(report_text)
        
    finally:
        # Cleanup
        print(f"\nCleaning up temporary repository at {repo_dir}...")
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)

if __name__ == "__main__":
    main()
