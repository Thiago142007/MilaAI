const fs = require('fs');
const buf = fs.readFileSync('src/client/models/gura/source/Gawr Gura.fbx');
const text = buf.toString('latin1');
const mats = text.match(/Material::[A-Za-z0-9_ -]+/g) || [];
const models = text.match(/Model::[A-Za-z0-9_ -]+/g) || [];
console.log('Materials found in FBX:');
console.log(Array.from(new Set(mats)));
console.log('Models/Meshes found in FBX:');
console.log(Array.from(new Set(models)));
