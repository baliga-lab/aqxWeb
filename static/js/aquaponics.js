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
             width: 360, height: 180,
             legend: { position: 'bottom', maxLines: 2},
             hAxis: { textPosition: 'none' }
         };
         chart.draw(data, options);
         return chart;
     };
}());