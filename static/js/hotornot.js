var setshowCookie = function(showCookie){
	showCookie = (typeof showCookie === "undefined") ? true : showCookie;
	if (document.cookie.indexOf('visited=true') === -1) {
	    var expires = new Date();
	    expires.setDate(expires.getDate()+30);
	    document.cookie = "visited=true; expires="+expires.toUTCString();
	    document.cookie = "visited=true; expires="+expires.toUTCString()+";domain=.smallestsample.com`;";
	    if(showCookie){
	    	$.colorbox({html:$('#popup_content').html(), width:"40%"});	
	    }
	    
	}
};


$('.hint-item').click(function(){$('#hints').slideToggle('slow')})