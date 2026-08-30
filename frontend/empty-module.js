// Stub for pdfjs-dist's optional Node "canvas" dependency. Text extraction in
// the browser never touches it, but the bundler still tries to resolve the
// require("canvas") in pdf.js's Node canvas factory — aliasing it here keeps
// the build from failing.
module.exports = {};
