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
        "numberOfUnits": parseFloat(units),
        "mealType": "other"
      }
    }
  },
  "id": Math.floor(Math.random() * 1000)
});

// Registro de la COMIDA ACTUALIZADA (tras consulta a la API)
console.log(logItem("Leche Entera", "794", "1136439", 2.5));
console.log(logItem("pasas", "35962", "58693", 5.0));
console.log(logItem("Avena", "51055285", "43281176", 1.0));
