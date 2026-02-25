const logItem = (name, foodId, servingId, units) => JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": { 
      "tool": "add_food_entry",
      "arguments": { 
        "foodId": foodId, 
        "foodEntryName": name,
        "servingId": servingId, 
        "numberOfUnits": units,
        "mealType": "other"
      }
    }
  },
  "id": Math.floor(Math.random() * 1000)
});

// Registro limpio de los ingredientes de las Gachas en 'Otros'
console.log(logItem("Avena Quaker", "51055285", "43281176", 1));
console.log(logItem("Leche Entera", "794", "1136439", 2.5));
