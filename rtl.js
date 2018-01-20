"use strict";

var timedOut = false;
setInterval(function() {
	timedOut = true;
}, 120000);

var observer = new MutationObserver(function(mutations) {
	// Wait till elements exist
	var editors = document.querySelectorAll('.ts-edit-box .cke_editable');
	var messageWrappers = document.querySelectorAll('.ts-message-list');
	var previewNodes = document.querySelectorAll('.chat-message-preview');

	if (editors.length === 0 || messageWrappers.length === 0 || previewNodes.length === 0) {
		if (timedOut) {
			observer.disconnect();
		}
		return;
	}
	observer.disconnect();

	var rtlifyElements = function(elements) {
		elements.forEach(function(elem) {
			elem.dir = 'auto';
		});
	}
	
	// RTL-ify editor(s)
	rtlifyElements(editors);
	
	// RTL-ify chat messages on DOM change
	var messagesObserver = new MutationObserver(function() {
		var messages = document.querySelectorAll('.message-body-content');
		rtlifyElements(messages);
	});
	var config = { childList: true, characterData: true, subtree: true };
	messageWrappers.forEach(function(wrapper) {
		messagesObserver.observe(wrapper, config);
	});
	
	// RTL-ify chat previews on DOM change
	var previewsObserver = new MutationObserver(function() {
		var previews = document.querySelectorAll('.ts-channel-list-entry-preview');
		rtlifyElements(previews);
	});
	previewNodes.forEach(function(node) {
		previewsObserver.observe(node, config);
	});
	
	// First time run - RTL all
	rtlifyElements(document.querySelectorAll('.message-body-content'));
	rtlifyElements(document.querySelectorAll('.ts-channel-list-entry-preview'));
});

observer.observe(document.body, {childList: true, subtree: true, attributes: false, characterData: false});