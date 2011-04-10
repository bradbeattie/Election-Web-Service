#!/usr/bin/python

# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ThreadingMixIn
from pyvotecore.plurality import Plurality
from pyvotecore.plurality_at_large import PluralityAtLarge
from pyvotecore.irv import IRV
from pyvotecore.stv import STV
from pyvotecore.schulze_method import SchulzeMethod
from pyvotecore.schulze_stv import SchulzeSTV
from pyvotecore.schulze_pr import SchulzePR
import json, types, StringIO, traceback, re

# This class provides a basic server to listen for JSON requests. It then
# calculates the winner using the desired voting system and returns the results,
# again, encoded in JSON.
class ElectionWebServiceHandler(BaseHTTPRequestHandler):
	
	def do_GET(self):
		response = '<html><body><h1>Election Web Service</h1><p>This server only responds to posts. Try sending something like this:</p><code>curl -d \'{"voting_system": "schulze_method", "notation": "ranking", "ballots": [{ "count":1, "ballot":{"A":1, "B":2, "C":3 }}, { "count":1, "ballot":{"A":1, "B":3, "C":2 }}, { "count":1, "ballot":{"A":3, "B":2, "C":1 }}]}\' http://vote.cognitivesandbox.com; echo;</code><p>For further documentation, see <a href="http://github.com/bradbeattie/Election-Web-Service">the GitHub project page</a>.</p></body></html>'
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.send_header("Content-length", str(len(response)))
		self.end_headers()
		self.wfile.write(response)

	
	def do_POST(self):
		try:
			# Parse the incoming data
			request_raw = self.rfile.read(int(self.headers["content-length"]))
			request_raw = re.sub("\n", "", request_raw)
			request = json.loads(request_raw)
			
			# Assume we're looking for a single winner
			if "winners" not in request:
				request["winners"] = 1
			else:
				request["winners"] = int(request["winners"])
			
			# Assume each ballot represents a single voter's preference
			new_input = []
			for ballot in request["ballots"]:
				if type(ballot) is not types.DictType:
					ballot = {"ballot":ballot}
				if "count" not in ballot:
					ballot["count"] = 1
				else:
					ballot["count"] = float(ballot["count"])
				new_input.append(ballot)
			request["ballots"] = new_input
			
			# Default the notation to ranking
			if "notation" not in request:
				request["notation"] = "ranking"
			
			# Send the data to the requested voting system
			if request["voting_system"] == "plurality":
				system = Plurality(request["ballots"])
			elif request["voting_system"] == "plurality_at_large":
				system = PluralityAtLarge(request["ballots"], request["winners"])
			elif request["voting_system"] == "irv":
				system = IRV(request["ballots"], request["winners"])
			elif request["voting_system"] == "stv":
				system = STV(request["ballots"], request["winners"])
			elif request["voting_system"] == "schulze_method":
				system = SchulzeMethod(request["ballots"], request["notation"])
			elif request["voting_system"] == "schulze_stv":
				system = SchulzeSTV(request["ballots"], request["winners"], request["notation"])
			elif request["voting_system"] == "schulze_pr":
				system = SchulzePR(request["ballots"], request["winners"], request["notation"])
			else:
				raise Exception("No voting system specified")
			response = system.as_dict()
			
			# Ensure a response came back from the voting system
			if response == None:
				raise
		
		except:
			fp = StringIO.StringIO()
			traceback.print_exc(10,fp)
			response = fp.getvalue()
			self.send_response(500)
		
		else:
			self.send_response(200)
		
		finally:
			response = json.dumps(self.__simplify_object__(response))
			self.send_header("Content-type", "application/json")
			self.send_header("Content-length", str(len(response)))
			self.end_headers()
			self.wfile.write(response)

	
	# json.dump() has a difficult time with certain object types
	def __simplify_object__(self, object):
		if type(object) == types.DictType:
			new_dict = {}
			for key in object.keys():
				value = self.__simplify_object__(object[key])
				key = self.__simplify_object__(key)
				new_dict[key] = value
			return new_dict
		elif type(object) == types.TupleType:
			new_list = []
			for element in object:
				new_list.append(self.__simplify_object__(element))
			return "(" + "|".join(new_list) + ")"
		elif type(object) == type(set()) or type(object) == types.ListType:
			new_list = []
			for element in object:
				new_list.append(self.__simplify_object__(element))
			return new_list
		else:
			return object

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	pass

def main():
	try:
		server = ThreadedHTTPServer(('localhost', 8044), ElectionWebServiceHandler)
		print('Webservice running...')
		server.serve_forever()
	except KeyboardInterrupt:
		print('Webservice stopping...')
		server.socket.close()

if __name__ == '__main__':
	main()
