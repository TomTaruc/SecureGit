# SecureGit Backend

This is the Flask/PostgreSQL backend for SecureGit.

## Runtime Compatibility

**Backend runtime: Python 3.11**
Python 3.13 is not currently supported because `psycopg2-binary==2.9.9` may fail to build.
Use Docker or a Python 3.11 virtual environment.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
