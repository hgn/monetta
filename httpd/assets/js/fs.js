"use strict";

async function RestGetRootDir(name)
{
  let response = await fetch(`/api/v1/fs?mode=root-dir`);
  let data = await response.json()
  return data;
}

function RestQueryDirectory(root_directory)
{
	let url = '/api/v1/fs?mode=file-listing&path=' + root_directory;
  fetch(url)
		.then(function(response) {
			return response.json()
		})
		.then(data => {
			updateFSTable(root_directory, data);
		})
		.catch(function(error) {
			console.log('Request failed', error)
		});
}

function tableHeader(root_directory)
{
	var str;
	str = "<b>" + root_directory + "</b>";
	str += '<table class="table table-borderless table-sm table-hover table-striped">  <thead><tr>';
	str += '<th>Path</th>'
	str += '<th>Filename</th>'
	str += '<th>Size</th>'
	str += '<th>User</th>'
	str += '<th>Group</th>'
	str += '<th>Mode</th>'
	str += '<th>MTime</th>'
	str += '</tr> </thead> <tbody> ';
	return str
}

function tableContent(data)
{
	var str = "";
	data['files'].forEach(function(entry) {
		str += '<tr>';
		str += '<td>' + entry['path'] + '</td>';
		str += '<td>' + entry['name'] + '</td>';
		str += '<td>' + entry['size'] + '</td>';
		str += '<td>' + entry['user'] + '</td>';
		str += '<td>' + entry['group'] + '</td>';
		str += '<td>' + entry['mode'] + '</td>';
		str += '<td>' + entry['mtime'] + '</td>';
		str += '</tr>';
	});
	return str;
}

function tableFooter()
{
	return '</tbody> </table>';
}

function tableInsert(data)
{
	let output = document.getElementById("fs-table");
	output.innerHTML += data;
}

function updateFSTable(root_directory, data)
{
	let entry;

	entry  = tableHeader(root_directory);
	entry += tableContent(data);
	entry += tableFooter();
	tableInsert(entry);
}

function ProcessRootDirData(data)
{
	let directories = data['directories'];
	directories.forEach(function(entry) {
		RestQueryDirectory(entry);
	});
}

$(document).ready(function() {
	RestGetRootDir().then(data => ProcessRootDirData(data));
});

