"""Streamlit UI Application dashboard for Repo Intelligence Agent.

Sets up a premium, responsive multi-tab interface for analyzing repositories,
explaining architectures, mapping issues, and performing evaluations.
"""

import streamlit as st


def set_premium_styles() -> None:
    """Injects custom CSS to create a premium glassmorphic dark mode dashboard."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Space+Grotesk:wght@400;600&display=swap');
        
        /* Font and Background styling */
        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif;
        }
        
        h1, h2, h3 {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 600;
        }

        /* Glassmorphic Container styling */
        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            margin-bottom: 20px;
        }

        /* Gradient Text Title styling */
        .gradient-title {
            background: linear-gradient(135deg, #FF8a00 0%, #E52E71 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 10px;
            text-align: left;
            letter-spacing: -1px;
        }
        
        /* Metric Card styling */
        .metric-value {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .metric-label {
            font-size: 0.9rem;
            color: #8c8c8c;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Renders the sidebar navigation and repository settings panel."""
    st.sidebar.markdown(
        "<h2 style='color:#FF8a00;'>⚙️ Settings</h2>", unsafe_allow_html=True
    )
    
    # Repository Input Config
    st.sidebar.text_input(
        "GitHub Repository URL",
        value="https://github.com/google/guava",
        placeholder="https://github.com/owner/repo",
        key="repo_url",
    )
    
    st.sidebar.text_input(
        "Branch / Ref",
        value="main",
        key="repo_ref",
    )
    
    st.sidebar.markdown("---")
    
    # Model Selection Config
    st.sidebar.selectbox(
        "LLM Model",
        options=["Gemini 2.5 Flash", "Gemini 2.5 Pro"],
        index=0,
        key="selected_model",
    )
    
    # API key configuration status indicators
    st.sidebar.markdown("### API Credentials Status")
    st.sidebar.info("🔑 GEMINI_API_KEY: Configured (Env)")
    st.sidebar.success("🎫 GITHUB_TOKEN: Active")


def render_explore_tab() -> None:
    """Renders the Repository Structure and Stack Analysis View."""
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### 📊 Repository Exploration & Stack Detection")
    st.write(
        "Analyze file structure, packages, dependencies, and core technologies of the target repository."
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='metric-label'>Languages</div>", unsafe_allow_html=True)
        st.markdown("<div class='metric-value'>Python, JS</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='metric-label'>Files Scanned</div>", unsafe_allow_html=True)
        st.markdown("<div class='metric-value'>42</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='metric-label'>Dependencies</div>", unsafe_allow_html=True)
        st.markdown("<div class='metric-value'>12</div>", unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Trigger Scan & Analysis", type="primary"):
        # TODO: Instantiate RepositoryAnalyzer and perform scanning
        st.warning("Analysis trigger placeholder. Business logic not implemented yet.")


def render_explainer_tab() -> None:
    """Renders the Architecture Summaries and Relationships View."""
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### 🏛️ Architecture Explanation")
    st.write(
        "Generates conceptual maps, module relationships, and guides developers on where to start reading."
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("Generate Architecture Explanations"):
        # TODO: Instantiate ArchitectureExplainer and generate summary
        st.warning("Explainer logic not implemented yet.")


def render_issue_mapper_tab() -> None:
    """Renders the GitHub Issues mapping and implementation planner View."""
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### 🎯 Issue Mapping & Implementation Planning")
    st.write("Import a GitHub issue or enter details manually to pinpoint target files and steps.")
    
    st.text_input("GitHub Issue URL / Title", placeholder="e.g. Fix memory leak in cache module")
    st.text_area("Issue Description", placeholder="Detailed logs or descriptions...", height=150)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("Generate Implementation Plan"):
        # TODO: Instantiate IssueMapper and execute mapping
        st.warning("Issue mapping and plan generation not implemented yet.")


def render_evaluator_tab() -> None:
    """Renders the Verification, hallucination checks, and evaluation dashboard View."""
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### ⚖️ Evaluation & Quality Guardrails")
    st.write(
        "Validates generated citations, detects potential model hallucinations, and outputs confidence scores."
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Display placeholders for recent evaluations
    st.info("No query logs evaluated yet. Submit a query to trigger evaluation validations.")


def main() -> None:
    """Main application runner orchestrating Streamlit settings and page elements."""
    st.set_page_config(
        page_title="Repo Intelligence Agent",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Load premium CSS
    set_premium_styles()
    
    # Title Header
    st.markdown("<div class='gradient-title'>Repo Intelligence Agent</div>", unsafe_allow_html=True)
    st.markdown(
        "##### *Kaggle Capstone Project: Multi-agent AI code comprehension assistant*"
    )
    
    # Sidebar
    render_sidebar()
    
    # Tabs layout
    tab_explore, tab_explainer, tab_issue, tab_eval = st.tabs(
        [
            "📊 Explore Repository",
            "🏛️ Architecture Explainer",
            "🎯 Issue Mapper",
            "⚖️ Evaluation Guardrails",
        ]
    )
    
    with tab_explore:
        render_explore_tab()
        
    with tab_explainer:
        render_explainer_tab()
        
    with tab_issue:
        render_issue_mapper_tab()
        
    with tab_eval:
        render_evaluator_tab()


if __name__ == "__main__":
    main()
