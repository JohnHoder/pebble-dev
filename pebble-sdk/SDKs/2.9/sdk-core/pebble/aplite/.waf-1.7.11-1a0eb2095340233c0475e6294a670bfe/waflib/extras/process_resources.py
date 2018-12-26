#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import json
import os,sys
import time
import re
import waflib
def process_font_cmd(script,ttf,pfo,entry):
	m=re.search('([0-9]+)',entry['name'])
	if m==None:
		if entry['name']!='FONT_FALLBACK':
			raise ValueError('Font {0}: no height found in name\n'.format(entry['name']))
		height=14
	else:
		height=int(m.group(0))
	extended='--extended'if entry.get('extended')else''
	tracking_adjust='--tracking %i'%entry['trackingAdjust']if'trackingAdjust'in entry else''
	character_regex='--filter "%s"'%entry['characterRegex'].encode('utf8')if'characterRegex'in entry else''
	character_list='--list "%s"'%entry['characterList']if'characterList'in entry else''
	legacy='--legacy'if entry.get('compatibility')=="2.7"else''
	cmd="python '{}' pfo {} {} {} {} {} {} '{}' '{}'".format(script,extended,height,tracking_adjust,character_regex,character_list,legacy,ttf,pfo)
	return cmd
def gen_resource_deps(bld,resources_dict,resources_path_node,output_pack_node,output_id_header_node,output_version_header_node,resource_header_path,tools_path,is_system=False,pfs_resources_header_node=None,font_key_header_node=None,font_key_table_node=None,font_key_include_path=None,timestamp=None):
	bitmap_script=tools_path.find_node('bitmapgen.py')
	font_script=tools_path.find_node('font/fontgen.py')
	pack_entries=[]
	font_keys=[]
	pfs_files=[]
	pfs_resources=[]
	def deploy_generator(entry):
		res_type=entry["type"]
		def_name=entry["name"]
		skip_copy=entry.get("skipCopy")
		input_file=str(entry["file"])
		input_node=resources_path_node.find_node(input_file)
		if input_node is None and not skip_copy:
			bld.fatal("Cound not find %s resource <%s>"%(res_type,input_file))
		if res_type=="raw":
			output_node=resources_path_node.get_bld().make_node(input_file)
			pack_entries.append((output_node,def_name))
			if not skip_copy:
				bld(rule="cp ${SRC} ${TGT}",source=input_node,target=output_node)
		elif res_type=="png":
			output_pbi=resources_path_node.get_bld().make_node(input_file+'.pbi')
			pack_entries.append((output_pbi,def_name))
			bld(rule="python '{}' pbi '{}' '{}'".format(bitmap_script.abspath(),input_node.abspath(),output_pbi.abspath()),source=[input_node,bitmap_script],target=output_pbi)
		elif res_type=="png-trans":
			output_white_pbi=resources_path_node.get_bld().make_node(input_file+'.white.pbi')
			output_black_pbi=resources_path_node.get_bld().make_node(input_file+'.black.pbi')
			pack_entries.append((output_white_pbi,def_name+"_WHITE"))
			pack_entries.append((output_black_pbi,def_name+"_BLACK"))
			bld(rule="python '{}' white_trans_pbi '{}' '{}'".format(bitmap_script.abspath(),input_node.abspath(),output_white_pbi.abspath()),source=[input_node,bitmap_script],target=output_white_pbi)
			bld(rule="python '{}' black_trans_pbi '{}' '{}'".format(bitmap_script.abspath(),input_node.abspath(),output_black_pbi.abspath()),source=[input_node,bitmap_script],target=output_black_pbi)
		elif res_type=="font":
			output_pfo=resources_path_node.get_bld().make_node(input_file+'.'+str(def_name)+'.pfo')
			fontgen_cmd=process_font_cmd(font_script.abspath(),input_node.abspath(),output_pfo.abspath(),entry)
			pack_entries.append((output_pfo,def_name))
			font_keys.append(def_name)
			bld(rule=fontgen_cmd,source=[input_node,font_script],target=output_pfo)
		else:
			waflib.Logs.error("Error Generating Resources: File: "+input_file+" has specified invalid type: "+res_type)
			waflib.Logs.error("Must be one of (raw, png, png-trans, font)")
			raise waflib.Errors.WafError("Generating resources failed")
	if timestamp==None:
		timestamp=int(time.time())
	for res in resources_dict["media"]:
		deploy_generator(res)
	if"files"in resources_dict:
		id_offset=len(pack_entries)
		for f in resources_dict["files"]:
			filename=f["name"]
			first_name=f["resources"][0]
			last_name=f["resources"][-1]
			pfs_files.append((first_name,last_name,filename,id_offset))
			for r in f["resources"]:
				pfs_resources.append(r);
			id_offset=id_offset+len(f["resources"])
	def create_node_with_suffix(node,suffix):
		return node.parent.find_or_declare(node.name+suffix)
	manifest_node=create_node_with_suffix(output_pack_node,'.manifest')
	table_node=create_node_with_suffix(output_pack_node,'.table')
	data_node=create_node_with_suffix(output_pack_node,'.data')
	md_script=tools_path.find_node('pbpack_meta_data.py')
	resource_code_script=tools_path.find_node('generate_resource_code.py')
	data_sources=[]
	table_string="python '{}' table '{}'".format(md_script.abspath(),table_node.abspath())
	manifest_string="python '{}' manifest {} '{}'".format(md_script.abspath(),manifest_node.abspath(),timestamp)
	content_string="python '{}' content '{}'".format(md_script.abspath(),data_node.abspath())
	resource_ids_header_string="python '{script}' resource_id_header ""'{output_header}'  '{resource_include}' ".format(script=resource_code_script.abspath(),output_header=output_id_header_node.abspath(),resource_include=resource_header_path)
	for entry in pack_entries:
		data_sources.append(entry[0])
		table_string+=' "%s" '%entry[0].abspath()
		manifest_string+=' "%s" '%entry[0].abspath()
		content_string+=' "%s" '%entry[0].abspath()
		resource_ids_header_string+=' "%s" '%str(entry[1])
	for entry in pfs_resources:
		resource_ids_header_string+=' "%s" '%str(entry)
	def touch(task):
		open(task.outputs[0].abspath(),'a').close()
	bld(rule=table_string,source=data_sources+[md_script],target=table_node)
	bld(rule=manifest_string,source=data_sources+[md_script],target=manifest_node)
	bld(rule=content_string,source=data_sources+[md_script],target=data_node)
	bld(rule="cat '{}' '{}' '{}' > '{}'".format(manifest_node.abspath(),table_node.abspath(),data_node.abspath(),output_pack_node.abspath()),source=[manifest_node,table_node,data_node],target=output_pack_node)
	bld(rule=resource_ids_header_string,source=resource_code_script,target=output_id_header_node,before=['c'])
	if is_system:
		resource_version_header_string="python '{script}' resource_version_header ""{version_def_name} '{output_header}' {timestamp} ""'{resource_include}' '{data_file}'".format(script=resource_code_script.abspath(),output_header=output_version_header_node.abspath(),version_def_name='SYSTEM_RESOURCE_VERSION',timestamp=timestamp,resource_include=resource_header_path,data_file=data_node.abspath())
		bld(rule=resource_version_header_string,source=[resource_code_script,data_node],target=output_version_header_node)
	if font_key_header_node and font_key_table_node and font_key_include_path:
		key_list_string=" ".join(font_keys)
		bld(rule="python '{script}' font_key_header '{font_key_header}' ""{key_list}".format(script=resource_code_script.abspath(),font_key_header=font_key_header_node.abspath(),key_list=key_list_string),source=resource_code_script,target=font_key_header_node)
		bld(rule="python '{script}' font_key_table '{font_key_table}' "" '{resource_id_header}' '{font_key_header}' {key_list}".format(script=resource_code_script.abspath(),font_key_table=font_key_table_node.abspath(),resource_id_header=output_id_header_node.abspath(),font_key_header=font_key_include_path,key_list=key_list_string),source=resource_code_script,target=font_key_table_node)
	if pfs_resources_header_node:
		pfs_resources_string=''
		for(first_name,last_name,filename,id_offset)in pfs_files:
			pfs_resources_string+="%s %s %s %s "%(first_name,last_name,filename,id_offset)
		bld(rule="python '{script}' pfs_files_header '{header}' ""'{resource_id_header}' {pfs_resources_string}".format(script=resource_code_script.abspath(),header=pfs_resources_header_node.abspath(),resource_id_header=output_id_header_node.abspath(),pfs_resources_string=pfs_resources_string),target=pfs_resources_header_node)
