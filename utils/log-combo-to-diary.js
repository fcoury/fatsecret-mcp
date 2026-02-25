const logItem = (name, foodId, servingId, units) => JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "add_food_entry",
      "arguments": { 
        "foodId": foodId, 
        "foodEntryName": name + " (Combo)",
        "servingId": servingId, 
        "numberOfUnits": parseFloat(units),
        "mealType": "breakfast"
      }
    }
  },
  "id": Math.floor(Math.random() * 1000)
});

// Ítems de 'Desayuno'
console.log(logItem("Jamón Serrano", "1497", "3569", 1.0));
console.log(logItem("Aceite de Oliva", "34212", "30460", 1.0));
console.log(logItem("Tostadas", "39130", "39465", 1.0));
console.log(logItem("Cola Cao Original", "4195532", "4083832", 1.0));
console.log(logItem("Leche Semidesnatada", "5516499", "5360439", 2.0));
