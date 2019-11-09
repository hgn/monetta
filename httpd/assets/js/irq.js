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
	str  = '<table class="table table-borderless table-sm table-hover table-striped">  <thead><tr>';
	str += '<th>IRQ</th>'
	var i;
	for (i = 0; i < noCPUs; i++) {
		str += '<th> CPU ' + i + '</th>';
	}
	str += '<th>INFO</th>'
	str += '<th>CPU Affinity</th>'
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

function irqRelativeColorPicker(diff) {
	const x = diff
	switch (true) {
			case (x < 5):
					return 'irq-update-rate-lowest';
					break;
			case (x < 10):
					return 'irq-update-rate-low';
					break;
			case (x < 25):
					return 'irq-update-rate-mid';
					break;
			case (x < 100):
					return 'irq-update-rate-high';
					break;
			default:
					return 'irq-update-rate-highest';
					break;
	}
}

function processIRQEntryRel(irq, data, noCPUs, interrupts, i)
{
	var str = "";

	if (irqDatPrev) {
		var prev_interrupts = irqDatPrev[irq].cpu[i];
		if (typeof prev_interrupts !== 'undefined' && prev_interrupts != interrupts) {
			let irq_diff = interrupts - prev_interrupts;
			let css_class = irqRelativeColorPicker(irq_diff);
			str += '<td class="' + css_class + '">' + irq_diff + '</td>';
		} else {
			str += '<td>' + '0' + '</td>';
		}
	} else {
		str += '<td>' + '0' + '</td>';
	}
	return str;
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
		if (irqMode == 'abs') {
		 str += processIRQEntryAbs(irq, data, noCPUs, interrupts, i);
		} else {
		 str += processIRQEntryRel(irq, data, noCPUs, interrupts, i);
		}
	}
	str += '<td>' + data.users + '</td>';
	str += '<td>' + data.affinity + '</td>';
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
