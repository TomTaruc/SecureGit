import json, os, subprocess, time
from app import create_app, db
from app.models.user import User
from app.models.ssh_key import SSHKey
from app.services.ssh_service import rebuild_authorized_keys

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='user1').first()
    if not user:
        print('User user1 not found')
        exit(1)

    # 1. Setup SSH key for root to push to user1
    key_path = '/root/.ssh/id_rsa'
    if not os.path.exists(key_path):
        os.makedirs('/root/.ssh', exist_ok=True)
        subprocess.run(['ssh-keygen', '-t', 'rsa', '-b', '2048', '-f', key_path, '-N', ''], check=True)
    
    with open(f'{key_path}.pub', 'r') as f:
        pub_key = f.read().strip()
    
    parts = pub_key.split()
    if len(parts) >= 2:
        fingerprint = f'e2e-test-key-{int(time.time())}'
        key_record = SSHKey(user_id=user.user_id, title='e2e', public_key=pub_key, fingerprint=fingerprint, key_type='ssh-rsa')
        db.session.add(key_record)
        db.session.commit()
        
        # sync keys
        keys = SSHKey.query.all()
        rebuild_authorized_keys([{'user_id': k.user_id, 'public_key': k.public_key, 'fingerprint': k.fingerprint} for k in keys])

    # 2. Create repo via API emulation
    from app.models.project import Project
    from app.models.repository import Repository
    from app.services import git_service, chroot_service

    proj_name = f'e2e-test-{int(time.time())}'
    repo_path = chroot_service.repo_path_for(user.username, proj_name)
    
    import pwd
    git_pwd = pwd.getpwnam('git')
    parent_dir = os.path.dirname(repo_path)
    os.makedirs(parent_dir, exist_ok=True)
    os.chown(parent_dir, git_pwd.pw_uid, git_pwd.pw_gid)
    os.makedirs(repo_path, exist_ok=True)
    os.chown(repo_path, git_pwd.pw_uid, git_pwd.pw_gid)
    git_service.git_init_bare(repo_path)
    
    project = Project(owner_user_id=user.user_id, project_name=proj_name, visibility='public', default_branch='main')
    db.session.add(project)
    db.session.flush()
    repo = Repository(project_id=project.project_id, repo_path=repo_path, clone_url=f'ssh://git@127.0.0.1:2222/{user.username}/{proj_name}.git', is_initialized=True)
    db.session.add(repo)
    db.session.commit()
    print(f'PROJECT_NAME={proj_name}')
