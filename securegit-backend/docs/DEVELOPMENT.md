# SecureGit Development

## Python Runtime Compatibility

**Backend runtime: Python 3.11**

Python 3.13 is not currently supported because `psycopg2-binary==2.9.9` may fail to build on some systems without proper headers or compilers under Python 3.13.

### Setup Instructions

To set up the development environment locally, please use Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r securegit-backend\requirements.txt
```

Alternatively, use Docker which is already configured with `python:3.11-slim`.
