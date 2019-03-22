jQuery.fn.ipAdderssOnly = function(){
    return this.each(function(){
        $(this).keydown(function(e){
			var code = e.keyCode || e.which;
			var sections = $(this).val().split('.');
			//Only check last section!
			var isInt       = ((code >= 48 && code <= 57) || (code >= 96 && code <= 105));
			if(isInt){
				if(sections.length < 4){
					//We can add another octet
					var val = parseInt(sections[sections.length-1]+String.fromCharCode(code));
					if(val > 255 || parseInt(sections[sections.length-1]) == 0){
						$(this).val($(this).val()+"."+String.fromCharCode(code));
						return false;
					}
					return true;
				} else {
					//Lets prevent string manipulations, our string is long enough
					var val = parseInt(sections[sections.length-1]+String.fromCharCode(code));
					if(val > 255 || parseInt(sections[sections.length-1]) == 0){
						return false;
					}
					return true;
				}
			} else if(code == 8 || code == 46 || code == 9 || code == 13){
				return true;
			}
			return false
		});
	});
}
window.jQuery.fn.numericOnly =
       function () {

           return this.each(function () {
               $(this).keydown(function (event) {
                   // Allow: backspace, delete, tab, escape, and enter
                   if (event.keyCode == 46 || event.keyCode == 8 || event.keyCode == 9 || event.keyCode == 27 || event.keyCode == 13 ||
                       // Allow: Ctrl+A
                       (event.keyCode == 65 && event.ctrlKey === true) ||
                       // Allow: home, end, left, right
                       (event.keyCode >= 35 && event.keyCode <= 39)) {
                       // let it happen, don't do anything
                       return;
                   } else {
                       // Ensure that it is a number and stop the keypress
                       if (event.shiftKey || (event.keyCode < 48 || event.keyCode > 57) && (event.keyCode < 96 || event.keyCode > 105)) {
                           event.preventDefault();
                       }
                   }
               });
           });
       };

$=jQuery
$(document).ready(function(){
	var o =$("table#sheduler")
	var b = o.find("tbody")
	var tFoot = o.find("tfoot");
	var deviceList=$("ul#devicesList")
	var deviceId="";
	var deviceActive=null
	var deviceActivators=[]
	var disonnector = $("button#disconnector")
	var mouseOnDisconnector = false;
	var wanIpAddrBox = $("tr#wanIpAddr > td:nth-child(2)")
	var deviceDescription= $("td#deviceDescription")
	editor = tFoot.find("tr#editor");
	shedulerRow=null;
	window.local=new Object();
	local.interface="SERIAL";
	local.port="COM4";
	local.ipAddr="127.0.0.1"
	local.tcpPort="1007";
	local.selectors=new Object();
	local.selectors.settings=$("tr#localSettings");
	$.extend(local.selectors,{
		connector:	local.selectors.settings.find("button#connectToSever"),
		ipaddr :	local.selectors.settings.find("tr#localIpAddr"),
		ipAddrCell: local.selectors.settings.find("tr#localIpAddr td:nth-child(2)"),
		serialport :local.selectors.settings.find("tr#selectPort > td > select"),
		interface :	local.selectors.settings.find("tr#selectInterface > td > select"),
		ipeditor :	local.selectors.settings.find("#localIpEditor"),
		ipcells :	local.selectors.settings.find("#localIpEditor input#localIpSelect"),
		tcpport: 	local.selectors.settings.find("#localIpEditor input#localPortSelect")
	});
	window.device=new Object()
	device.selectors=new Object()
	device.selectors.settings=$("table#deviceSettings")
	$.extend(device.selectors,{
		ipaddr:		device.selectors.settings.find("tr#deviceIpAddr > td:nth-child(2)")
	})
	function shedulerRowButtons(a){
		if (typeof a === "undefined" || a === null)
			a = b.find("tr.editable");
		a.find("td:nth-last-child(2)").click(function(){
			$(this).parent().remove();
		})
		a.find("td:nth-last-child(1)").click(function(){
			var t=$(this).parent();
			shedulerRow=lineValues(t);
			for(var e in editorValues){ 
				editorValues[e](shedulerRow[e]())
			}
			editor.css({top:0});
			var p = (editor.position().top)-(t.position().top);
			editor.css({ top:p*(-1) , visibility:"visible" });
		})
	}
	shedulerRowButtons()
	function evp(element){
		var g = editor.find(element)
		return function(a){
			if (typeof a === "undefined" || a === null)
				return g.val()
			g.val(a) 
		}
	}

	function lga(parent,element,attr){
		var h = parent.children("td:nth-child("+element+')');
		return function(v){
			if (typeof v === "undefined" || v === null) 
				return h.attr(attr);
			else  h.attr(attr,v);
		}
	}
	
	function lineValues(p){ 
		return {
			id:			lga(p,1,"in"),
			minute:		lga(p,2,"minute"),
			hour:		lga(p,2,"hour"),
			timemode:	lga(p,3,"dtimemode"),
			action:		lga(p,4,"action")
		}
	}
	editorValues={
		id: (function(){ 
			var h=editor.find("td:first-child");
			return function (i){
				if (typeof i === "undefined" || i === null)
					return h.html()
				else h.html(i)
			}})(),
		hour:		evp("input#hour"),
		minute:		evp("input#minute"),
		timemode:	evp("select#timemode"),
		action:		evp("select#mode")
		
	}
	
	editor.find("td:nth-last-child(1)").click(function(){
		for(var e in editorValues) 
			shedulerRow[e]( editorValues[e]() )
		editor.css({visibility:"hidden"});
	})
	datepicker = editor.find("input#datepicker");
	//datepicker.datepicker()
	//datepicker.datepicker("option", "dateFormat",'y/mm/dd')
	timemode = editor.find("select#timemode")
	datemode = $("<option></option>");
	timemode.append(datemode)
	datepicker.datepicker({
        onSelect: function(date) {
			datemode.attr("value",date);
			datemode.html(date);
            timemode.val(date);
        },
        showOn: "button",
        buttonImageOnly: true,
        dateFormat:'y/mm/dd',
        buttonText: "_"
	} )
	datepicker.hide();
	
	timemode.change(function(e){
		if (this.value == "date") {
			datepicker.datepicker("show")
		}
	})
	
	editing=null;
	window.makeShedulerTable=function(m){
		var y,d,g,r,h,z;
		z=$("table#sheduler > tbody");
		z.find("tr.editable").remove()
		d=$('<tr><td></td><td></td><td></td><td></td><td></td><td></td></tr>').attr("class","editable");
		r=lineValues(d);
		y=m.split(',');
		for (var f=0; f<y.length; f++){
			g=y[f].split("-")
			if ( g === null ) continue;
			r.id(f);
			h = g[1].split(":")
			r.hour(h[0])
			r.minute(h[1])
			r.action(g[2])
			r.timemode(g[0])
			if(d[0].children.length>0)
				shedulerRowButtons(d.clone().appendTo(z));
		}
	}
	
	window.readShedulerTable=function(){
		var s = [];
		b.children("[class='editable']").each(function(){
			var a = lineValues($(this))
			s.push(a.timemode() + '-' + a.hour() +':'+ a.minute() + '-' + a.action())
		})
		return s
	}
	
	$("button#addShedulerRecord").click(function(){
		var c=$('<tr><td></td><td></td><td></td><td></td><td></td><td></td></tr>').attr("class","editable")
		var op=lineValues(c);
		var l = b.find("> tr:last-child");
		if ( l.length >= 1 ) op.id(parseInt(lga(l,1,"in")())+1);
		else op.id("0")
		op.hour("00")
		op.minute("00")
		op.timemode("daily")
		c.appendTo(b);
		shedulerRowButtons(c);
		
	})
	
	$("button#applyShedulerValues").click(function(){
			var n=">"+JSON.stringify([deviceId,{"charm":readShedulerTable()}])
			console.log(n)
			socket.send(n)
	})
	
	local.selectors.interface.on('change',function(e){
		local.interface = this.value;
		var bridgePortRow = local.selectors.serialport.parent().parent();
		if ( this.value == "SERIAL" ) {
			window.socket.send('+SERIAL');
			bridgePortRow.css({"visibility":"visible"})
			local.selectors.ipaddr.hide();
		} else {
			window.socket.send('+TCP');
			bridgePortRow.css({"visibility":"hidden"})
			local.selectors.ipaddr.show();
		}
	})
	local.selectors.ipcells.ipAdderssOnly();
	local.selectors.tcpport.numericOnly();
	local.selectors.ipeditor.css({'top':(-1)*(function(y){
		return (y.position().top)-(local.selectors.ipaddr.position().top);
	})(local.selectors.ipeditor)});

	local.selectors.ipeditor.find("td:last-child").click(function(){
		var g = local.selectors.ipcells.val();
		var f = local.selectors.tcpport.val();
		$(this).parent().css({"visibility":"hidden"});
		local.tcpPort=f;
		local.ipAddr=g;
		local.selectors.ipAddrCell.html(g+":"+f)
		window.socket.send('~'+g+':'+f);
	})
	local.selectors.ipAddrCell.html(local.ipAddr+':'+local.tcpPort)
	local.selectors.ipaddr.find("td:last-child").click(function(){
		local.selectors.ipeditor.css({"visibility":"visible"})
		adress=local.selectors.ipAddrCell.html().split(":")
		local.selectors.ipcells.val(adress[0])
		local.selectors.tcpport.val(adress[1])
	})
	
	local.selectors.serialport.change(function(){ 
		window.socket.send('$'+ $(this).val());
	})
	
	local.selectors.connector.click(function(){
		var state = window.socket.readyState;
		if ( state < 2 ) window.socket.close()
		else connect()
	})
	
	disonnector.mouseover(function(){ mouseOnDisconnector=true })
	disonnector.mouseout(function(){
		setTimeout(function(){ mouseOnDisconnector=false; },50); 
	})
	disonnector.click(function(){
		disonnector.hide()
		window.socket.send('@unplug '+deviceActive.attr('in'))
	})
	
	var clearDeviceEvents=function(){
		deviceActive.unbind('mouseover')
		deviceActive.unbind('mouseout')
	}
	var deactivateDevices=function(){
		$(deviceActivators).each(function(){
			$(this).removeAttr("checked");
		})
	}
	
	function connect(){
	try{
		var host = "ws://"+local.ipAddr+":"+local.tcpPort;
		window.socket = new WebSocket(host);
		socket.binaryType = "arraybuffer";
		socket.onopen = function(){
			local.selectors.connector.html("Rozłącz")
			local.selectors.interface.trigger( "change" );
		//	console.log('<p class="event">Socket Status: '+socket.readyState+' (open)');
		}
		socket.onmessage = function(msg){
			if(msg.data[0]=="@"){
				var cmd = msg.data.substring(1).split(' ')
				var json = cmd.slice(2).join(' '); 
				switch(cmd[0]) {
					case "update":
						a = deviceList.find("li[in=\""+cmd[1]+"\"]")
						$.each($.parseJSON(json),function (atr,val){
							if ( a.is("["+atr+"]") ) a.attr(atr,val)
							if (atr == "class" && val=="disconnected"){
								clearDeviceEvents()
								deactivateDevices()
								disonnector.hide()
							}
						})
						break;
					case "hostaddr":
						wanIpAddrBox.html(cmd[1])
						break;
						
				}
			}
			if(msg.data[0]=="!") 
				if ( msg.data == "!ERROR" ) deactivateDevices()
				else if ( msg.data == "!OK" ) console.log("Device activated.");
			if(msg.data[0]=="$") {
				var a = $("<option></option>")
				local.selectors.serialport.html("");
				var g = msg.data.substring(1).split('%');
				$(g).each(function(){
					a.html(this);
					a.val(this);
					a.clone().appendTo(local.selectors.serialport);
				})
			}
			if(msg.data[0]=="#"){
				var sub = 1
				if(msg.data[1]!="*"){
					deviceList.children().remove();
				} else sub = 2
				var data = jQuery.parseJSON(msg.data.substring(sub))
				var offset=0;
				var len=data.length;
				var attributes=[""];
				var onAttr=0;
				var onDevice=0;
				var c=0;
				var row=null;
				var sel=$('<input type="radio" name="dev"/>');
				var span=$('<span><span>')
				var rowon=null;
				var makerow=function(a){		
					row=$("<li></li>");
					row.attr("class",a["status"]);
					row.attr("cron",a["settings"]["charm"]);
					row.attr("desc",a["settings"]["desc"]);
					row.attr("ip",a["ip"]);
					row.attr("port",a["port"]);
					row.attr("in",a["csgn"]);
					//sel.attr("i",a["settings"]["id"])
					span.html(a["settings"]["name"]);
					rowon=row.clone()
					deviceActivators.push(sel.clone().appendTo(rowon).click(function() {
						socket.send("!"+$(this).parent().attr("in"))
					}))
					span.clone().appendTo(rowon)
					rowon.appendTo(deviceList);
					rowon.click(function(){
						deviceId=$(this).attr("in");
						makeShedulerTable($(this).attr("cron"));
						deviceDescription.html($(this).attr("desc"))
						device.selectors.ipaddr.html(
							$(this).attr("ip")+":"+
							$(this).attr("port")
						)
						if ( deviceActive != null ){
							deviceActive.attr("active","False")

						}
						deviceActive=$(this)
						if (deviceActive.is("[class=connected]")){
							var offset=deviceActive.offset()
							disonnector.css({
								'left':offset.left+110+
								'px','top':offset.top+8+'px'
							})
							deviceActive.mouseover(function(){ disonnector.show() })
							deviceActive.mouseout(function(){ if(!mouseOnDisconnector) disonnector.hide() })	
							disonnector.show()
						}
						deviceActive.attr("active","True")
					})
				}
				while(offset<len){
					c = data[offset]
					makerow(c);
					offset+=1
				}
			}
		}
		socket.onclose = function(){
			console.log('<p class="event">Socket Status: '+socket.readyState+' (Closed)');
			local.selectors.connector.html("Połącz");
			//setTimeout(function(){connect();},5000);
		}			
	} catch(exception){
		console.log('<p>Error'+exception);
	}
}
	connect();
})
