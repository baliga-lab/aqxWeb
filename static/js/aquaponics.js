var aqx;
if (!aqx) {
    aqx = {};
}
(function () {
    "use strict";

     aqx.makeTimeSeriesData = function(ylabels, rows) {
         var data = new google.visualization.DataTable();
         data.addColumn('string', 'Time');
         for (var i = 0; i < ylabels.length; i++)
             data.addColumn('number', ylabels[i]);
         data.addRows(rows);
         return data;
     };

     aqx.drawChart = function(elementId, label, data) {
         var chart = new google.visualization.LineChart(document.getElementById(elementId));
         var options = {
             title: label,
             width: 280, height: 120,
             legend: { position: 'bottom', maxLines: 2},
             hAxis: { textPosition: 'none' }
         };
         chart.draw(data, options);
         return chart;
     };

     var phStops = [0xfaac59, 0xee8243, 0xe35744, 0xe93e4d, 0xea185e];
     var nh4Stops = [0xffe26d, 0xdde093, 0xc7dd8a, 0x9dd29c, 0x88b789];
     var no3Stops = [0xfffaed, 0xf9abcc, 0xf581b2, 0xe92b93, 0xde0084, 0xd50078];
     var no2Stops = [0xfefcf0, 0xfdf6f1, 0xfcecec, 0xfdb8d4, 0xf6a1c0, 0xfa91b3];
     var clStops = [0xffffff, 0xfaf7ea, 0xf2e6f0, 0xf4ccda, 0xf7b5d6, 0xf6acce];
     var hardStops = [0x737255, 0x7e7358, 0x906048, 0xa55942, 0xd66f52];
     var alkStops = [0xeac766, 0xb7b278, 0xa1a97e, 0x748c7b, 0x6a8079, 0x5f6773];

     aqx.phGradientColor = function(rangeStart, rangeStop, current) {
         return gradientColor(rangeStart, rangeStop, current, phStops);
     };
     aqx.nh4GradientColor = function(rangeStart, rangeStop, current) {
         return gradientColor(rangeStart, rangeStop, current, nh4Stops);
     };
     aqx.no3GradientColor = function(rangeStart, rangeStop, current) {
         return gradientColor(rangeStart, rangeStop, current, no3Stops);
     };
     aqx.no2GradientColor = function(rangeStart, rangeStop, current) {
         return gradientColor(rangeStart, rangeStop, current, no2Stops);
     };
     aqx.clGradientColor = function(rangeStart, rangeStop, current) {
         return gradientColor(rangeStart, rangeStop, current, clStops);
     };
     aqx.hardGradientColor = function(rangeStart, rangeStop, current) {
         return gradientColor(rangeStart, rangeStop, current, hardStops);
     };
     aqx.alkGradientColor = function(rangeStart, rangeStop, current) {
         return gradientColor(rangeStart, rangeStop, current, alkStops);
     };

     function gradientColor(rangeStart, rangeStop, current, stops) {
         var numRangeValues = rangeStop - rangeStart;
         var numStops = stops.length;
         var segmentLength = numRangeValues / (numStops - 1);
         var segment = Math.floor(current / segmentLength); // which segment are we in ?
         var stop0 = stops[segment];
         var stop1 = stops[segment + 1];

         // calculate the resulting color between stop0 and stop1 by interpolating
         // the RGB colors. We do this by extracting the components, converting
         // into HSV, then interpolate and convert back to RGB
         var comps0 = rgbComponents(stop0);
         var comps1 = rgbComponents(stop1);
         var offset = (current - (segmentLength * segment));
         var fraction = offset / (segmentLength - 1);
         var resultRGB = {
             'r': interpolate(comps0.r / 255.0, comps1.r / 255.0, fraction),
             'g': interpolate(comps0.g / 255.0, comps1.g / 255.0, fraction),
             'b': interpolate(comps0.b / 255.0, comps1.b / 255.0, fraction)
         };
         var finalRGB = mergeRGB(Math.round(resultRGB.r * 255.0),
                                 Math.round(resultRGB.g * 255.0),
                                 Math.round(resultRGB.b * 255.0));
         var fc = finalRGB.toString(16);
         return '#' + fc;
     };

     function interpolate(from, to, fraction) {
         return (to - from) * fraction + from;
     }

     function rgbComponents(c) {
         return { 'r': (c >> 16) & 0xff, 'g': (c >> 8) & 0xff, 'b': c & 0xff };
     }

     function mergeRGB(r, g, b) {
         return ((r << 16) & 0xff0000) | ((g << 8) & 0xff00) | (b & 0xff);
     }

     // Interaction for gradient pickers and form inputs
     // See system_details.html, these functions assume the presence of elements
     // whose ids follow a certain name convention
     aqx.updateStripValues = function(posx, prefix, rangeMin, rangeMax, gradientFun) {
         var stripWidth = $('#' + prefix + '-strip').css('width');
         stripWidth = parseInt(stripWidth.substring(0, stripWidth.length - 2));
         if (posx > stripWidth) posx = stripWidth;
         $('#' + prefix + '-picker').css({left: posx, top: -1, position: "absolute"});
         var rangeSize = rangeMax - rangeMin;
         var value = rangeMin + (posx * (rangeSize / stripWidth));
         $('#' + prefix + '-value').attr('value', value.toFixed(2));
         var previewColor = gradientFun(0, stripWidth, posx);
         $('#' + prefix + '-preview').css({'background-color': previewColor});
     };

     aqx.connectStrip = function(prefix, updateFun) {
         function mouseEvent(e, jqThis) {
             var posx = e.pageX - jqThis.offset().left;
             updateFun(posx);
         }
         $('#' + prefix + '-strip').click(function (e) { mouseEvent(e, $(this)); });
         $('#' + prefix + '-strip').mousedown(function () { isDragging = true; })
             .mousemove(function (e) { if (isDragging) mouseEvent(e, $(this)); })
             .mouseup(function () { isDragging = false; });
     };

}());