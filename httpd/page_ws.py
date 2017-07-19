from aiohttp import web

async def handle(request):
    d = b"""
<!DOCTYPE html>
<html>
<head>
<script type="text/javascript">

    window.addEventListener("load", function() {

        try{
            var mySocket = new WebSocket('ws://' + window.location.host + '/ws');
        }
        catch(err) {
            var mySocket = new WebSocket('wss://' + window.location.host + '/ws');
        }

        var log_data = [];

        // add event listener reacting when message is received
        mySocket.onmessage = function (event) {

            jdata = JSON.parse(event.data);

            if ('data-log-entry' in jdata) {
                log_data.push(jdata['data-log-entry']);

                var output = document.getElementById("output-log");

                var newstr = ""
                for (var i = log_data.length - 1; i > 0; i--) {
                    newstr = newstr + log_data[i].MESSAGE + "<br />";
                }
                output.innerHTML = newstr;
            } else if ('data-info' in jdata) {

                if ('list-comm' in jdata['data-info']) {

                    var comm_entries = jdata['data-info']['list-comm'];

                    var newstr = ""
                    for (var i = comm_entries.length - 1; i > 0; i--) {
                        newstr = newstr + comm_entries[i] + "<br />";
                    }
                    var output = document.getElementById("output-info");
                    output.innerHTML = newstr;
                } else {
                    console.log("data not handled");
                }

            } else {
                console.log("data not handled");
            }


        };


        var form = document.getElementsByClassName("foo");
        var input = document.getElementById("input");
        form[0].addEventListener("submit", function (e) {
            // on forms submission send input to our server
            input_text = input.value;
            mySocket.send(input_text);
            e.preventDefault()
        })
    });
</script>
<style>
    div {
        margin: 10em;
    }
    form {
        margin: 10em;
    }
</style>
</head>
<body>
    <form class="foo">
        <input id="input"></input>
        <input type="submit"></input>
    </form>
    <div id="output-log"></div>
    <div id="output-info"></div>
</body>
</html>
"""
    return web.Response(body=d, content_type='text/html')
