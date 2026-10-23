/* Generated from hub.json by kit/render_hub.py. Sends a visitor of a page that
   moved to another account's GitHub Pages site there, keeping the rest of the
   path, the ?lang= choice and the #hash. */
(function () {
  var moved = {"AI-Intune": "https://ted-h-com.github.io", "AI-Sister": "https://ted-h-com.github.io", "Control-AI-Chat": "https://ted-h-com.github.io", "TokenMonster": "https://ted-h-com.github.io", "Web_Comfyui": "https://ted-h-com.github.io", "agentic-smart-home": "https://ted-h-com.github.io", "agy-openai-shim": "https://ted-h-com.github.io", "ai-brainstorming": "https://ted-h-com.github.io", "ai-security-scanner": "https://ted-h-com.github.io", "bat-agent-connector": "https://ted-h-com.github.io", "bat-cowork": "https://ted-h-com.github.io", "claude-idea-review-skill": "https://ted-h-com.github.io", "clawd-lobster": "https://ted-h-com.github.io", "idn-homograph-example": "https://ted-h-com.github.io", "mcp-memory-server": "https://ted-h-com.github.io", "metamuse-cli": "https://ted-h-com.github.io", "multi-ai-chat": "https://ted-h-com.github.io", "multi-ai-chat-desktop": "https://ted-h-com.github.io", "multi-ai-terminal": "https://ted-h-com.github.io", "openclaw-hermes-watcher": "https://ted-h-com.github.io", "reset-therapy": "https://ted-h-com.github.io", "zhan-dou-tuo-luo": "https://ted-h-com.github.io"};
  var path = window.location.pathname;
  var slug = path.split("/")[1];
  if (Object.prototype.hasOwnProperty.call(moved, slug) && moved[slug] !== window.location.origin) {
    window.location.replace(moved[slug] + path + window.location.search + window.location.hash);
  }
})();
