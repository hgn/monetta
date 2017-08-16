"use strict";

var mySocket;
var journalEntryArray = [];

$(document).ready(function() {

	if(!("WebSocket" in window)){
		console.log("browser support no web sockets");
		return;
	} else {
		initWebSockets();
	}

});

function wsOnOpen(event) {
	console.time("WS");
    mySocket.send("start");
    mySocket.send("info");
}

// this is why JS is so f*cking stupid, see callsites
function addZero(x, n) {
	while (x.toString().length < n) {
		x = "0" + x;
	}
	return x;
}

function journalRealTimeToHuman(time) {
	// time is in microseconds, we need in milli,
	// which is fine for now
	var date = new Date(time / 1000);

	var year = date.getFullYear();
	var month = date.getMonth() + 1;
	var day = date.getDate();

	var hours = addZero(date.getHours(), 2);
	var minutes = addZero(date.getMinutes(), 2);
	var seconds = addZero(date.getSeconds(), 2);
	var milliseconds = addZero(date.getMilliseconds(), 3);
	return year + "-" + month + "-" + day + " " + hours + ':' +
		     minutes + ':' + seconds + "." + milliseconds;
}

function journalSaveNewEntry(entry) {
	// we do converations once, not every time we draw them
	var message = "no message";
	if ('MESSAGE' in entry) {
		message = entry['MESSAGE'];
	}

	// uid, gid and pid
	var uid = "unknown";
	if ('_UID' in entry) {
		uid = entry['_UID'];
	}
	var gid = "unknown";
	if ('_GID' in entry) {
		gid = entry['_GID'];
	}
	var pid = "unknown";
	if ('_PID' in entry) {
		pid = entry['_PID'];
	}

	// misc
	var transport = "unknown";
	if ('_TRANSPORT' in entry) {
		transport = entry['_TRANSPORT'];
	}
	var cmdline = "unknown";
	if ('_CMDLINE' in entry) {
		cmdline = entry['_CMDLINE'];
	}
	var comm = "unknown";
	if ('_COMM' in entry) {
		comm = entry['_COMM'];
	}

	// time
	var realtime = "error";
	if ('__REALTIME_TIMESTAMP' in entry) {
		realtime = journalRealTimeToHuman(entry['__REALTIME_TIMESTAMP']);
	}

	var human_prio = "unknown"
	if ('PRIORITY' in entry) {
		var prio = entry['PRIORITY'];
		if (prio == 0) {
			human_prio = 'emerg';
		} else if (prio == 1) {
			human_prio = 'alert';
		} else if (prio == 2) {
			human_prio = 'crit';
		} else if (prio == 3) {
			human_prio = 'err';
		} else if (prio == 4) {
			human_prio = 'warning';
		} else if (prio == 5) {
			human_prio = 'notice';
		} else if (prio == 6) {
			human_prio = 'info';
		} else if (prio == 7) {
			human_prio = 'debug';
		}
	}

	var element = {
		message: message,
		priority: human_prio,
		uid: uid,
		gid: gid,
		pid: pid,
		cmdline: cmdline,
		transport: transport,
		comm: comm,
		realtime: realtime
	};

	journalEntryArray.push(element);
}

function itemSelectPriorityColor(entry) {
	switch (entry.priority) {
			case "emerg":
				return 'item-emerg';
			case "alert":
				return 'item-alert';
			case "crit":
				return 'item-crit';
			case "err":
				return 'item-err';
			case "warning":
				return 'item-warning';
			case "notice":
				return 'item-notice';
			case "info":
				return 'item-info';
			case "debug":
				return 'item-debug';
			default:
				return 'item-unknown';
	}
}

function journalEntryConstructSubtitle(entry) {
	var str = "com: " + entry.comm
		+ ' / prio: ' + entry.priority
	  + ' / pid: ' +  entry.pid
	  + ' / uid: ' +  entry.uid
	  + ' / gid: ' +  entry.gid
	  + ' / cmdline: ' +  entry.cmdline
	  + ' / transport: ' +  entry.transport;
	return str
}

function processJournalEntriesData(data) {
	journalSaveNewEntry(data)

	var newstr = ""
	for (var i = journalEntryArray.length - 1; i > 0; i--) {
		//console.log(journalEntryArray[i]);
		newstr = newstr
			+ '<a href="#myModal" data-toggle="modal" class="list-group-item list-group-item-action flex-column align-items-start '
		  + itemSelectPriorityColor(journalEntryArray[i]) + '">'
		  + '<div class="d-flex w-100 justify-content-between"> <h5 class="mb-1">'
			+ journalEntryArray[i].message
		  + '</h5><small>'
		  + journalEntryArray[i].realtime
			+ ' </small></div><small class="text-supermuted">'
		  + journalEntryConstructSubtitle(journalEntryArray[i])
		  + '</small></a>';
	}

	var output = document.getElementById("anchor-journal");
	output.innerHTML = newstr;
}

function processJournalInfoData(data) {
				if ('list-comm' in data) {
					var comm_entries = data['list-comm'].sort().reverse();
					var newstr = '<div class="btn-group" role="group" aria-label="Basic example">'
								+ '<button type="button" class="btn btn-secondary btn-sm">Deselect All</button>'
								+ '<button type="button" class="btn btn-secondary btn-sm">Select All</button>'
								+ '</div><hr />'
					for (var i = comm_entries.length - 1; i > 0; i--) {
						newstr = newstr +
							'<div class="form-check"><label class="form-check-label">' +
							'<input class="form-check-input" type="checkbox" value=""> ' +
						   comm_entries[i] +
							'</label></div>';
					}
					var output = document.getElementById("process-list");
					output.innerHTML = newstr;
				}
}

function wsOnMessage(event) {
		console.timeEnd("WS");
			var jdata = JSON.parse(event.data);
			if ('data-log-entry' in jdata) {
				processJournalEntriesData(jdata['data-log-entry']);
			} else if ('data-info' in jdata) {
				processJournalInfoData(jdata['data-info']);
			} else {
				console.log("data not handled");
			}
}

function initWebSockets() {
	try {

		try {
			mySocket = new WebSocket('ws://' + window.location.host + '/ws-journal');
		}
		catch(err) {
			mySocket = new WebSocket('wss://' + window.location.host + '/ws-journal');
		}

		mySocket.onmessage = wsOnMessage;
    mySocket.onopen    = wsOnOpen;


	} catch(exception){
		console.log('Error' + exception);
	}
}
