from subprocess import call
import requests
import json
import xml.etree.ElementTree as ET

#result = requests.get("http://trips.ihmc.us/parser/cgi/parse?input=This+is+a+test+sentence")
#print (result.text)
#root = ET.fromstring(result.text)
#print(root)
#for node in root:
#    print(node)
#data = json.loads(result.text)
print ("Running Blender...")
call(["blender", "blocks_world3.blend", "--background", "--python", "main.py"])
#print (result)
