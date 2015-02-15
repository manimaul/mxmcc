/**
 * Created by will on 8/4/14.
 */

function read_text(url, mime) {
    var request = new XMLHttpRequest();
    request.open('GET', url, false);
    request.overrideMimeType(mime);
    try {
        request.send();
        if (request.status != 0) {
            console.log('read_text', request.status, request.responseText);
        }
    } catch (e) {
        console.log('read_text', e.code);
        if (e.code == 101) {
            console.error('Google Chrome requires to run with "--allow-file-access-from-files" switch to load XML from local files')
        }
    }
    return request.responseText;
}

function read_metadata() {
    var tilemap_txt = read_text("metadata.json", "application/json");
    if (tilemap_txt == null) {
        error('Cannot read tilemap.json');
        return null;
    }

    return JSON.parse(tilemap_txt);
}