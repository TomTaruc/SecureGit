from app import create_app
app = create_app()
with app.app_context():
    from app.services import ssh_service
    try:
        ssh_service.add_key(1, "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIH5wKYUk3sZtgNRN2K70147JlrNgGwB8pS+f8EVN81eL root@docker")
        print("SUCCESS")
    except Exception as e:
        print("ERROR:", repr(e))
