import tak_to_mesh;
import mesh_to_tak;
import threading;
import time;

def ttm():
    tak_to_mesh.tak_to_mesh();

def mtt():
    mesh_to_tak.mesh_to_tak();

#start thread for tak_to_mesh
t0=threading.Thread(target=ttm());
t0.start();
time.sleep(2);

#run mesh_to_tak on main thread
mtt();
