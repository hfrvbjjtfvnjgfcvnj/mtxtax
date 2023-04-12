import re

test_string='Possible Surveillance Aircraft Position Acquired||Comment: SPY PLANE\n\
Operator: US AIR FORCE SPECIAL OPERATIONS COMMAND/A5KM\n\
Time: 2023-04-10 20:34:09\n\
Model: PILATUS PC-12\n\
Distance: 64.16 miles\n\
Reg: N581PC\n\
Bearing: 315 (NW)\n\
Hex Code: a77ae7\n\
Latitude: 30.876984\n\
Longitude: -86.440645\n\
ICAO Type: L1T\n\
FAA Type: fixed wing - single engine\n\
http://192.168.1.124/dump1090/gmap.html\n\
https://globe.adsbexchange.com/?feed=kq68j55a9Kku\n\
https://globe.adsbexchange.com/?icao=a77ae7'

print(test_string);

lines=test_string.split("\n");
first=True
filtered=""
for line in lines:
    
    if first or "Operator: " in line or "Bearing: " in line or "ICAO Type: " in line or "Distance: " in line or "Model: " in line:
        #print(line);
        filtered=filtered+("%s\n"%line);
    else:
        #print("####%s"%line);
        pass
    first=False;
filtered=filtered.replace("||","\n");
filtered=re.sub(".*: ","",filtered);
print(filtered);