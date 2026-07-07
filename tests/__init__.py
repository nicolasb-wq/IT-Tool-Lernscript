# Markiert tests/ als reguläres Python-Paket. Ohne diese Datei legt Pytest im
# Standard-Importmodus nur tests/ selbst auf den sys.path — das Repo-Root mit
# dem app-Paket bleibt unauffindbar (CI-Fehler: "No module named 'app'").
