module.exports = function(module) {
    switch(module) {
        case "message_keys": return require("message_keys");
    }
    throw new Error('Module not found: ' + module);
};
