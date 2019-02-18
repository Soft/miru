
$(function() {
	var frames = $(".slideshow li");
	var current = frames.first();
	window.setInterval(function() {
		current.fadeOut("slow");
		current = current.is(frames.last()) ? frames.first() : current.next();
		current.fadeIn("slow");
	}, 5000);
});

