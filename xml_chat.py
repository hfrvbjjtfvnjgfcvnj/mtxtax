import xml.etree.ElementTree as ET

chat='<?xml version="1.0" encoding="UTF-8"?>\n<event version="2.0" uid="GeoChat.S-1-5-21-4020722038-864290438-423658893-1001.All Chat Rooms.e0450884-aaca-4fa7-85fa-1445d43198fa" type="b-t-f" how="h-g-i-g-o" time="2023-04-10T18:20:00Z" start="2023-04-10T18:20:01Z" stale="2023-04-11T18:20:01Z"><point lat="0.0" lon="0.0" hae="9999999.0" ce="9999999.0" le="9999999.0"/><detail><__chat id="All Chat Rooms" chatroom="All Chat Rooms" senderCallsign="THWG-WinTAK" groupOwner="false" messageId="e0450884-aaca-4fa7-85fa-1445d43198fa"><chatgrp id="All Chat Rooms" uid0="S-1-5-21-4020722038-864290438-423658893-1001" uid1="All Chat Rooms"/></__chat><link uid="S-1-5-21-4020722038-864290438-423658893-1001" type="a-f-G-E-V-C" relation="p-p"/><remarks source="BAO.F.WinTAK.S-1-5-21-4020722038-864290438-423658893-1001" sourceID="S-1-5-21-4020722038-864290438-423658893-1001" to="All Chat Rooms" time="2023-04-10T18:20:01.02Z">Roger</remarks><_flow-tags_ TAK-Server-3e85cf16864b4af9be9bc677439ee0b4="2023-04-10T18:20:00Z"/></detail></event>';

root=ET.fromstring(chat);

print(root.find("detail/__chat").attrib['senderCallsign'])

remarks=root.findtext("detail/remarks");
if remarks is not None:
    print(remarks)
