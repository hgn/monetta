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
    ws_socket.send("start-irq-update");
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
			if ('data-irq' in jdata) {
        console.log('update irq data');
				processIrqData(jdata['data-irq'], jdata['no-cpus']);
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


function processTableHeader(noCPUs) {
	var str;
	str  = '<table class="table table-borderless table-sm table-hover table-striped">  <thead class="thead-dark"><tr>';
	str += '<th>IRQ</th>'
	var i;
	for (i = 0; i < noCPUs; i++) {
		str += '<th> CPU ' + i + '</th>';
	}
	str += '<th>INFO</th>'
	str += '</tr> </thead> <tbody> ';
	return str
}


function processIRQEntry(irq, data, noCPUs) {
	var str;

	str = '<tr><td>' + irq + '</td>';
	var i;
	for (i = 0; i < noCPUs; i++) {
		var interrupts = '∅';
		if (i in data.cpu) {
			interrupts = data.cpu[i];
		}
		if (irqDatPrev) {
			var prev_interrupts = irqDatPrev[irq].cpu[i];
			if (typeof prev_interrupts !== 'undefined' && prev_interrupts != interrupts) {
				console.log(prev_interrupts);
				str += '<td class="update-cell">' + interrupts + '</td>';
			} else {
				str += '<td>' + interrupts + '</td>';
			}
		} else {
			str += '<td>' + interrupts + '</td>';
		}
	}
	str += '<td>' + data.users + '</td>';
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

function processIrqData(irqData, noCPUs) {

	let output = document.getElementById("irq-table");
	let str = processTableHeader(noCPUs);
  for (const [key, value] of Object.entries(irqData).sort(integerStringSort)) {
		str += processIRQEntry(key, value, noCPUs);
  }
	str += processTableFooter();
	output.innerHTML = str;
	irqDatPrev = irqData;
}
