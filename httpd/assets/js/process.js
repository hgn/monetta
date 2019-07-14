"use strict";

var ws_socket;


$(document).ready(function() {


	if(!("WebSocket" in window)){
		console.log("browser support no web sockets");
		return;
	} else {
		initWebSockets();
	}
});


function wsOnOpen(event) {
    ws_socket.send("start-process-update");
}

function wsOnMessage(event) {
			var jdata = JSON.parse(event.data);
			if ('process-data' in jdata) {
        console.log('update process data');
				processProcessData(jdata['process-data']);
			} else {
				console.log("data not handled");
			}
}

function initWebSockets() {
	try {
		console.log("use unencryped web socket for data exchange");
		ws_socket = new WebSocket('ws://' + window.location.host + '/ws-process');
	}
	catch(err) {
		try {
			ws_socket = new WebSocket('wss://' + window.location.host + '/ws-process');
		} catch(exception){
			console.log('Error' + exception);
		}
	}

	ws_socket.onmessage = wsOnMessage;
	ws_socket.onopen    = wsOnOpen;
}


function processTableHeader() {
	return '<table class="table table-sm table-hover">' +
		'<thead><tr>' +
		'<th>PID</th>' +
		'<th>Comm</th>' +
		'<th>EUID</th>' +
		'<th>EGID</th>' +
		'<th>Policy</th>' +
		'<th>Nice</th>' +
		'<th>Priority</th>' +
		'<th>RT Priority</th>' +
		'<th>Wchan</th>' +
		'<th>Syscall</th>' +
		'<th>CPUs Allowed</th>' +
		'<th>CAP Eff</th>' +
		'</tr> </thead> <tbody> '
}


function processTableEntry(entry) {
	return '<tr>' +
		       '<td>' + entry['pid'] + '</td>' +
		       '<td>' + entry['comm'] + '</td>' +
		       '<td>' + entry['euid'] + '</td>' +
		       '<td>' + entry['egid'] + '</td>' +
		       '<td>' + entry['policy'] + '</td>' +
		       '<td>' + entry['nice'] + '</td>' +
		       '<td>' + entry['priority'] + '</td>' +
		       '<td>' + entry['rt-priority'] + '</td>' +
		       '<td>' + entry['wchan'] + '</td>' +
		       '<td>' + entry['syscall'] + '</td>' +
		       '<td>' + entry['cpus-allowed-list'] + '</td>' +
		       '<td>' + entry['cap-eff'] + '</td>' +
		      '</tr>';
}

function processTableFooter() {
	return '</tbody> </table>'
}


function processProcessData(rawData) {
	let output = document.getElementById("process-table");

	let str = processTableHeader();
  for (const [key, value] of Object.entries(rawData['data']).sort((a, b) => a - b)) {
		str += processTableEntry(value);
  }
	str += processTableFooter();
	output.innerHTML = str;
}
