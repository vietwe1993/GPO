import os
import ldap3

LDAP_SERVER = '192.168.193.10'
LDAP_USER = 'mocap\\administrator'
LDAP_PASSWORD = 'hoimocap@2014'
BASE_DN = 'CN=Policies,CN=System,DC=mocap,DC=hcmc'
SYSVOL_PATH = r"\\192.168.193.10\SYSVOL\mocap.hcmc\Policies"

# Kết nối LDAP
server = ldap3.Server(LDAP_SERVER, get_info=ldap3.ALL)
conn = ldap3.Connection(server, user=LDAP_USER, password=LDAP_PASSWORD, auto_bind=True)

# Truy vấn tất cả GPO object
conn.search(BASE_DN, '(objectClass=groupPolicyContainer)', attributes=['name', 'displayName', 'whenCreated'])

for entry in conn.entries:
    gpo_guid = entry.name.value
    ad_display_name = entry.displayName.value
    created = entry.whenCreated.value

    # Đọc thêm từ GPT.ini trong SYSVOL
    gpt_path = os.path.join(SYSVOL_PATH, gpo_guid, "GPT.INI")
    file_display_name = None
    if os.path.exists(gpt_path):
        with open(gpt_path, 'r') as f:
            for line in f:
                if line.strip().lower().startswith("displayname"):
                    file_display_name = line.strip().split('=')[1]
                    break

    print(f"[GPO] {file_display_name or ad_display_name} | GUID: {gpo_guid} | Created: {created}")
