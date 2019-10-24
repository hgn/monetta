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

var irqMode = 'abs';

function initButtonGroup() {
	console.log('register');
	$('#toggle-rel').on('change', function () {
		irqMode = 'rel';
	});

	$('#toggle-abs').on('change', function () {
		irqMode = 'abs';
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
	str += '<th>RSS</th>'
	str += '<th>USS</th>'
	str += '<th>PSS</th>'
	str += '</tr> </thead> <tbody> ';
	return str
}

function processIRQEntryAbs(irq, data, noCPUs, interrupts, i)
{
	var str = "";

	if (irqDatPrev) {
		var prev_interrupts = irqDatPrev[irq].cpu[i];
		if (typeof prev_interrupts !== 'undefined' && prev_interrupts != interrupts) {
			str += '<td class="update-cell">' + interrupts + '</td>';
		} else {
			str += '<td>' + interrupts + '</td>';
		}
	} else {
		str += '<td>' + interrupts + '</td>';
	}
	return str;
}

function processIRQEntryRel(irq, data, noCPUs, interrupts, i)
{
	var str = "";

	if (irqDatPrev) {
		var prev_interrupts = irqDatPrev[irq].cpu[i];
		if (typeof prev_interrupts !== 'undefined' && prev_interrupts != interrupts) {
			str += '<td class="update-cell">' + (interrupts - prev_interrupts) + '</td>';
		} else {
			str += '<td>' + '0' + '</td>';
		}
	} else {
		str += '<td>' + '0' + '</td>';
	}
	return str;
}


function processIRQEntry(key, value) {
	var str;

	str = '<tr>';
	str += '<td>' + key + '</td>';
	str += '<td>' + value.comm + '</td>';
	str += '<td>' + value.rss + '</td>';
	str += '<td>' + value.Uss + '</td>';
	str += '<td>' + value.Pss + '</td>';
	str += '</tr>';
	return str;
}

function processTableFooter() {
	return '</tbody> </table>'
}

function integerStringSort(a, b) {
  if (isNaN(a[0]) || isNaN(b[0])) {
    return a[0] > b[0] ? 1 : -1;
  }
  return a[0] - b[0];
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
