
import sys
import os
up_dir = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(up_dir)
from shadow import Shadow

s   = Shadow()
s.forward_all()

