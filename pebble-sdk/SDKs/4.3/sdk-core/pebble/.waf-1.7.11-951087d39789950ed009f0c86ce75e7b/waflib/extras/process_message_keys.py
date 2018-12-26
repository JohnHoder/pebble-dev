#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import json
from re import findall
from waflib.TaskGen import before_method,feature
from waflib import Logs,Task
from sdk_helpers import get_node_from_abspath
header=("""#pragma once
#include <stdint.h>

//
// AUTOGENERATED BY BUILD
// DO NOT MODIFY - CHANGES WILL BE OVERWRITTEN
//

""")
definitions_file=("""
#include <stdint.h>

//
// AUTOGENERATED BY BUILD
// DO NOT MODIFY - CHANGES WILL BE OVERWRITTEN
//

""")
def configure(conf):
	if conf.env.BUILD_TYPE!='lib':
		if not dict(conf.env.PROJECT_INFO).get('enableMultiJS',False):
			Logs.pprint("CYAN","WARNING: enableMultiJS is not enabled for this project. message_keys.json ""will not be included in your project unless you add it to your ""pebble-js-app.js file.")
	keys=conf.env.PROJECT_INFO.get('messageKeys',conf.env.PROJECT_INFO.get('appKeys',[]))
	if conf.env.BUILD_TYPE=='rocky':
		if keys:
			conf.fatal("Custom messageKeys are not supported for Rocky.js projects. Please ""remove any messageKeys listed in your package.json file.")
		else:
			keys={"ControlKeyResetRequest":1,"ControlKeyResetComplete":2,"ControlKeyChunk":3,"ControlKeyUnsupportedError":4,}
	key_list=[]
	key_dict={}
	block_message_keys=[]
	if keys:
		if isinstance(keys,list):
			key_list=keys
		elif isinstance(keys,dict):
			if conf.env.BUILD_TYPE=='lib':
				conf.fatal("Libraries can only specify an array of messageKeys; other object types ""are not supported.")
			key_dict=keys
		else:
			conf.fatal("You have specified an invalid messageKeys object in your project JSON ""file.")
	combined_key_list=key_list+key_dict.keys()
	for lib in conf.env.LIB_JSON:
		if not'pebble'in lib or not'messageKeys'in lib['pebble']:
			continue
		lib_keys=lib['pebble']['messageKeys']
		if isinstance(lib_keys,list):
			for key in lib_keys:
				if key in combined_key_list:
					conf.fatal("The messageKey '{}' has already been used and cannot be re-used by ""the {} library.".format(key,lib['name']))
				combined_key_list.append(key)
			key_list.extend(lib_keys)
		else:
			conf.fatal("'{}' has an invalid messageKeys object. ""Libraries can only specify an messageKeys array.".format(lib['name']))
	if key_list:
		next_key=10000
		multi_keys=[key for key in key_list if']'in key]
		single_keys=[key for key in key_list if']'not in key]
		for key in multi_keys:
			try:
				key_name,num_keys=findall(r"([\w]+)\[(\d+)\]$",key)[0]
			except IndexError:
				suggested_key_name=key.split('[',1)[0]
				conf.fatal("An invalid message key of `{}` was specified. Verify that a valid ""length is specified if you are trying to allocate an array of keys ""with a single identifier. For example, try `{}[2]`.".format(key,suggested_key_name))
			else:
				key_dict.update({key_name:next_key})
				next_key+=int(num_keys)
				block_message_keys.append(key_name)
		key_dict.update({value:key for key,value in enumerate(single_keys,start=next_key)})
	conf.env.PROJECT_INFO['messageKeys']=key_dict
	conf.env.PROJECT_INFO['appKeys']=key_dict
	conf.env.MESSAGE_KEYS=key_dict
	conf.env.BLOCK_MESSAGE_KEYS=block_message_keys
	bld_dir=conf.path.get_bld()
	conf.env.MESSAGE_KEYS_HEADER=bld_dir.make_node('include/message_keys.auto.h').abspath()
	if key_dict:
		conf.env.MESSAGE_KEYS_DEFINITION=bld_dir.make_node('src/message_keys.auto.c').abspath()
		conf.env.MESSAGE_KEYS_JSON=bld_dir.make_node('js/message_keys.json').abspath()
@feature('message_keys')
@before_method('cprogram','process_js','process_headers')
def process_message_keys(task_gen):
	message_keys=task_gen.env['MESSAGE_KEYS']
	bld=task_gen.bld
	header_task=(task_gen.create_task('message_key_header',tgt=get_node_from_abspath(task_gen.bld,getattr(task_gen.env,'MESSAGE_KEYS_HEADER'))))
	header_task.message_keys=message_keys
	header_task.dep_vars=message_keys
	if bld.env.BUILD_TYPE=='lib'or not message_keys:
		return
	definitions_task=(task_gen.create_task('message_key_definitions',tgt=get_node_from_abspath(task_gen.bld,getattr(task_gen.env,'MESSAGE_KEYS_DEFINITION'))))
	definitions_task.message_keys=message_keys
	definitions_task.dep_vars=message_keys
	bld.path.get_bld().make_node('js').mkdir()
	json_task=(task_gen.create_task('message_key_json',tgt=get_node_from_abspath(task_gen.bld,getattr(task_gen.env,'MESSAGE_KEYS_JSON'))))
	json_task.message_keys=message_keys
	json_task.dep_vars=message_keys
@Task.update_outputs
class message_key_header(Task.Task):
	def run(self):
		self.outputs[0].parent.mkdir()
		with open(self.outputs[0].abspath(),'w')as f:
			f.write(header)
			for k,v in sorted(self.message_keys.items(),key=lambda x:x[0]):
				f.write("extern uint32_t MESSAGE_KEY_{};\n".format(k))
@Task.update_outputs
class message_key_definitions(Task.Task):
	def run(self):
		self.outputs[0].parent.mkdir()
		with open(self.outputs[0].abspath(),'w')as f:
			f.write(definitions_file)
			for k,v in sorted(self.message_keys.items(),key=lambda x:x[0]):
				f.write("uint32_t MESSAGE_KEY_{} = {};\n".format(k,v))
@Task.update_outputs
class message_key_json(Task.Task):
	def run(self):
		self.outputs[0].parent.mkdir()
		with open(self.outputs[0].abspath(),'w')as f:
			json.dump(self.message_keys,f,sort_keys=True,indent=4,separators=(',',': '))
