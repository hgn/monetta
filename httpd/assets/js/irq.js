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
    //ws_socket.send("start-process-update");
}

function wsOnMessage(event) {
			var jdata = JSON.parse(event.data);
			if ('process-data' in jdata) {
        console.log('update irq data');
				processProcessData(jdata['process-data']);
			} else {
				console.log("data not handled");
			}
}

function initWebSockets() {
	try {
		console.log("use unencryped web socket for data exchange");
		ws_socket = new WebSocket('ws://' + window.location.host + '/ws-irq');
	}
	catch(err) {
		try {
			ws_socket = new WebSocket('wss://' + window.location.host + '/ws-irq');
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
		'<th>Wchan</th>' +
		'<th>Syscall</th>' +
		'<th>CPU Set</th>' +
		'</tr> </thead> <tbody> '
}


function processTableEntry(entry) {
	return '<tr>' +
		       '<td>' + entry['pid'] + '</td>' +
		       '<td>' + entry['comm'] + '</td>' +
		       '<td>' + entry['wchan'] + '</td>' +
		       '<td>' + entry['syscall'] + '</td>' +
		       '<td>' + entry['cpu-set'] + '</td>' +
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
