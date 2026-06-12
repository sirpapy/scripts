def ldap_auth(domain, username, password, authorized_groups=None):
    try:
        from MYLibrary import users
    except ImportError:
        return False

    login = f"{domain}\\{username}"

    for group in authorized_groups or []:
        try:
            group_users = users.list_group_users(group, login, password)
        except ValueError:
            return False

        if username in group_users:
            return True

    return False
