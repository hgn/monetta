"use strict";

var ws_socket;


$(document).ready(function() {
	if(!("WebSocket" in window)){
		console.log("browser support no web sockets");
		return;
	} else {
		initWebSockets();
	}

	initButtonGroup();
});

var memory_sort_key = 'Uss';

function initButtonGroup() {
	$('#toggle-memory-pid').on('change', function () {
		memory_sort_key = 'pid';
	});

	$('#toggle-memory-comm').on('change', function () {
		memory_sort_key = 'comm';
	});

	$('#toggle-memory-uss').on('change', function () {
		memory_sort_key = 'Uss';
	});

	$('#toggle-memory-pss').on('change', function () {
		memory_sort_key = 'Pss';
	});

	$('#toggle-memory-rss').on('change', function () {
		memory_sort_key = 'Rss';
	});

	$('#toggle-memory-referenced').on('change', function () {
		memory_sort_key = 'Referenced';
	});

	$('#toggle-memory-anonymous').on('change', function () {
		memory_sort_key = 'Anonymous';
	});

	$('#toggle-memory-locked').on('change', function () {
		memory_sort_key = 'Locked';
	});
}


function wsOnOpen(event) {
    ws_socket.send("start-memory-update");
}

var info_updates_no = 0;

function infoUpdates(data) {
	var processing_time = '∅';
	if ('processing-time' in data) {
		processing_time = data['processing-time'];
	}
	info_updates_no += 1;
	document.getElementById("info-processing-time").innerHTML = processing_time;
	document.getElementById("info-updates").innerHTML = info_updates_no;
}

function wsOnMessage(event) {
			var jdata = JSON.parse(event.data);
			infoUpdates(jdata);
			if ('data-memory' in jdata) {
				processMemoryData(jdata['data-memory']);
			} else {
				console.log("data not handled");
			}

}

function initWebSockets() {
	try {
		console.log("use unencryped web socket for data exchange");
		ws_socket = new WebSocket('ws://' + window.location.host + '/ws-memory');
	}
	catch(err) {
		try {
			ws_socket = new WebSocket('wss://' + window.location.host + '/ws-memory');
		} catch(exception){
			console.log('Error' + exception);
		}
	}
	ws_socket.onmessage = wsOnMessage;
	ws_socket.onopen    = wsOnOpen;
}


function processTableHeader() {
	var str;
	str  = '<table class="table table-borderless table-sm table-hover table-striped">  <thead><tr>';
	str += '<th>PID</th>'
	str += '<th>Name</th>'
	str += '<th>Command Line</th>'
	str += '<th>USS</th>'
	str += '<th>PSS</th>'
	str += '<th>RSS</th>'
	str += '<th>Referenced</th>'
	str += '<th>Anonymous</th>'
	str += '<th>Locked</th>'
	str += '</tr> </thead> <tbody> ';
	return str
}

function humanBytes(fileSizeInBytes) {
    var i = -1;
	  if (fileSizeInBytes <= 0)
		    return fileSizeInBytes;
    var byteUnits = [' kB', ' MB', ' GB', ' TB', 'PB', 'EB', 'ZB', 'YB'];
    do {
        fileSizeInBytes = fileSizeInBytes / 1024;
        i++;
    } while (fileSizeInBytes > 1024);

    return Math.max(fileSizeInBytes, 0.1).toFixed(1) + byteUnits[i];
};

function processIRQEntry(key, value) {
	var str;

	str = '<tr>';
	str += '<td>' + key + '</td>';
	str += '<td>' + value.comm + '</td>';
	str += '<td>' + value.cmdline.substring(0, 90) + '</td>';
	str += '<td>' + humanBytes(value.Uss) + '</td>';
	str += '<td>' + humanBytes(value.Pss) + '</td>';
	str += '<td>' + humanBytes(value.Rss) + '</td>';
	str += '<td>' + humanBytes(value.Referenced) + '</td>';
	str += '<td>' + humanBytes(value.Anonymous) + '</td>';
	str += '<td>' + humanBytes(value.Locked) + '</td>';
	str += '</tr>';
	return str;
}

function processTableFooter() {
	return '</tbody> </table>'
}

function integerStringSort(a, b) {
	let key_a = a[1][memory_sort_key];
	let key_b = b[1][memory_sort_key];
	if (memory_sort_key == 'pid') {
		return key_a > key_b ? 1 : -1;
	}
	if (memory_sort_key == 'comm') {
		return key_a.toLowerCase().localeCompare(key_b.toLowerCase());
	}
	// Fallback, we show highest number first
	if (isNaN(key_a) || isNaN(key_b)) {
		return key_a < key_b ? 1 : -1;
	}
	return key_b - key_a;
}

var irqDatPrev = null;

function processMemoryData(irqData) {
	let output = document.getElementById("process-memory-table");
	let str = processTableHeader();
  for (const [key, value] of Object.entries(irqData).sort(integerStringSort)) {
		str += processIRQEntry(key, value);
  }
	str += processTableFooter();
	output.innerHTML = str;
	irqDatPrev = irqData;
}
