## Embedding-stage isolation diagnostics (temporary)

- Add stdout prints in:
  - services/embedding_service.py
    - _get_model(): ENTER/Loading/loaded
    - generate_embeddings_batch(): encode workload size + ENTER/EXIT model.encode()
  - backend/api.py
    - before embedding: total chunks + total characters

Run:
1) Restart uvicorn backend
2) Replay failing POST /api/analyze
3) Capture last output lines and determine:
   - whether model load hangs
   - whether encode hangs
   - whether chunk explosion is happening
