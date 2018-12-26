var fs = require('fs');

module.exports = function(source) {
    // Set this loader to cacheable
    this.cacheable();

    // Whitelist files in the current project
    var whitelisted_folders = [this.options.context];

    // Whitelist files from the SDK-appended search paths
    whitelisted_folders = whitelisted_folders.concat(this.options.resolve.root);

    // Iterate over whitelisted file paths
    for (var i=0; i<whitelisted_folders.length; i++) {
        // If resource file is from a whitelisted path, return source
        if (~this.resourcePath.indexOf(fs.realpathSync(whitelisted_folders[i]))) {
            return source;
        }
    }

    // If the resource file is not from a whitelisted path, emit an error and fail the build
    this.emitError("Requiring a file outside of the current project folder is not permitted.");
    return "";
};
