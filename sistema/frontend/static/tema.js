"use strict";
// Aplica o tema salvo antes de a página desenhar (evita o clarão). Sem armazenamento, fica no tema noite.
try { if (localStorage.getItem("pz-tema") === "dia") document.documentElement.setAttribute("data-theme", "light"); } catch (e) { /* sem armazenamento */ }
