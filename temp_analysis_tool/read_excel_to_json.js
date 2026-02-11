const XLSX = require('xlsx');
const filename = '../cuentas_extraidas.xlsx';

try {
    const workbook = XLSX.readFile(filename);
    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    const data = XLSX.utils.sheet_to_json(sheet);
    console.log(JSON.stringify(data));
} catch (e) {
    console.error(e);
    console.log("[]"); 
}
