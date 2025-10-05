// Shared JS for VittCott static site
document.addEventListener('DOMContentLoaded', function(){
  // floating assistant button opens ai-assistant.html in a new window or panel
  const floatBtn = document.getElementById('float-open');
  const openAiBtn = document.getElementById('open-ai-btn');
  if(floatBtn) floatBtn.addEventListener('click', ()=> { window.location.href = 'ai-assistant.html'; });
  if(openAiBtn) openAiBtn.addEventListener('click', ()=> { window.location.href = 'ai-assistant.html'; });

  // helper for in-page prompt open (used on index)
  window.openAssistantWithPrompt = function(prompt){
    // navigate to assistant page and prefill via query param
    const url = new URL(window.location.origin + '/ai-assistant.html');
    if(prompt) url.searchParams.set('q', prompt);
    window.location.href = url.toString();
  };

  // prefill chat input when opening assistant with ?q=...
  try {
    if(window.location.pathname.endsWith('/ai-assistant.html')){
      const p = new URLSearchParams(window.location.search).get('q');
      if(p){
        const input = document.getElementById('chat-input');
        if(input){ input.value = p; input.focus(); }
      }
    }
  } catch(e){ /* ignore */ }
});
