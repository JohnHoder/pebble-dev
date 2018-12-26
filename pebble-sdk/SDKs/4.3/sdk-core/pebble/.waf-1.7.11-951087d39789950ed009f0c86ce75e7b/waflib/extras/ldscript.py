#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

from waflib import Utils,Errors,Node
from waflib.TaskGen import after,feature
@after('apply_link')
@feature('cprogram','cshlib')
def process_ldscript(self):
	if not getattr(self,'ldscript',None)or self.env.CC_NAME!='gcc':
		return
	def convert_to_node(node_or_path_str):
		if isinstance(node_or_path_str,basestring):
			return self.path.make_node(node_or_path_str)
		else:
			return node_or_path_str
	if isinstance(self.ldscript,basestring)or isinstance(self.ldscript,list):
		ldscripts=Utils.to_list(self.ldscript)
	else:
		ldscripts=[self.ldscript]
	nodes=[convert_to_node(node)for node in ldscripts]
	for node in nodes:
		if not node:
			raise Errors.WafError('could not find %r'%self.ldscript)
		self.link_task.env.append_value('LINKFLAGS','-T%s'%node.abspath())
		self.link_task.dep_nodes.append(node)
