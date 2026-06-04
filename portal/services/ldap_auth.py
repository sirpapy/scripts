def ldap_auth(domain, username, password, authorized_groups=None):
    try:
        from MYLibrary import users
    except ImportError:
        return False

    login = f"{domain}\\{username}"

    for group in authorized_groups or []:
        if username in users.list_group_users(group, login, password):
            return True

    return False
