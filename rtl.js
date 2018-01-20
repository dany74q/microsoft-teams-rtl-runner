var rtlifyElements = function(elements) {
	elements.forEach(function(elem) {
		elem.dir = 'auto';
	});
}

// RTL-ify editor(s)
var editors = document.querySelectorAll('.ts-edit-box .cke_editable');
rtlifyElements(editors);

// RTL-ify chat messages on DOM change
var messagesObserver = new MutationObserver(function() {
	messages = document.querySelectorAll('.message-body-content');
	rtlifyElements(messages);
});
var config = { childList: true, characterData: true, subtree: true };
var messageWrappers = document.querySelectorAll('.ts-message-list');
messageWrappers.forEach(function(wrapper) {
	messagesObserver.observe(wrapper, config);
});

// RTL-ify chat previews on DOM change
var previewsObserver = new MutationObserver(function() {
	var previews = document.querySelectorAll('.ts-channel-list-entry-preview');
	rtlifyElements(previews);
});
var previewNodes = document.querySelectorAll('.chat-message-preview');
previewNodes.forEach(function(node) {
	previewsObserver.observe(node, config);
});

// First time run - RTL all
rtlifyElements(document.querySelectorAll('.message-body-content'));
rtlifyElements(document.querySelectorAll('.ts-channel-list-entry-preview'));