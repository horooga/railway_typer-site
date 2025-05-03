Service's user-defined(PORT - for healthcheck) and shared(MONGO_PUBLIC_URL - for the mongodb service connection) vars:

+----MongoDB-----+    +--typer-app---+
|vars:           | +->|vars:         |
|MONGO_PUBLIC_URL|-+  |PORT:8000     |
|                |    |              |
+----------------+    +--------------+
