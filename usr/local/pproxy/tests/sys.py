from pystemd.systemd1 import Unit
unit = Unit(b'sshd.service')
unit.load()
print(unit.__dict__)
if unit.Unit.ActiveState==b'active':
    print("Active")
else:
    print("Not active")
