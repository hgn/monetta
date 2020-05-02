"use strict";

async function RestGetRootDir(name)
{
  let response = await fetch(`/api/v1/fs?mode=root-dir`);
  let data = await response.json()
  return data;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function FileQuery(path)
{
	let url = '/api/v1/fs?mode=files&path=' + path;
	try {
		let response = await fetch(url);
		let data = await response.json()
		return data;
	}
	catch(err) {
		return [];
	}
}


function tableContent(entry)
{
	return "<tr><td>" + entry.path + "</td>" +
		'<td>' + entry.size + '</td>' +
		'<td>' + entry.user + '</td>' +
		'<td>' + entry.group + '</td>' +
		'<td>' + entry.mode + '</td>' +
		'<td>' + entry.mtime + '</td>' +
    "</tr>";
}


function tableInsert(data)
{
	document.getElementById("fs-table").innerHTML += data;
}

function updateFSTable(root_directory, data)
{
	tableInsert(tableContent(data));
}

var no_files = 0;
var bytes_files = 0;
var largest_file_size = 0;
var largest_file_path = 0;

function bytesToSize(bytes)
{
   var sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
   if (bytes == 0) return '0 Byte';
   var i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
   return Math.round(bytes / Math.pow(1024, i), 2) + ' ' + sizes[i];
}

function updateFileInfo(entry)
{
	no_files += 1;
	bytes_files += entry.size;
  if (largest_file_size < entry.size) {
    largest_file_size = entry.size;
    largest_file_path = entry.path;
  }
	let data  = "Files & Directoroes: " + no_files + "<br />";
      data += "Size: " + bytesToSize(bytes_files) + "<br />";
      data += "Largest File " + largest_file_path + ", Size: " + bytesToSize(largest_file_size) + "<br />";
	document.getElementById("file-info").innerHTML = data;
}

async function ProcessFileQuery(data)
{
	for(const entry of data){
		if (entry.type == 'directory') {
			updateFSTable('/', entry);
			let query = await FileQuery(entry.path)
			await ProcessFileQuery(query)
		} else {
			updateFSTable('/', entry);
		}
		updateFileInfo(entry);
	}
}

$(document).ready(function() {
	FileQuery('/').then(data => ProcessFileQuery(data));
});

