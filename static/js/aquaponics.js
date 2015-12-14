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
}());