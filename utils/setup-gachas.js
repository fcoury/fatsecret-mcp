const addItem = (mealId, foodId, name, servingId, units) => JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "add_food_to_meal",
      "arguments": { 
        "mealId": mealId, 
        "foodId": foodId, 
        "mealItemName": name,
        "servingId": servingId, 
        "numberOfUnits": units
      }
    }
  },
  "id": Math.floor(Math.random() * 1000)
});

const logItem = (name, foodId, servingId, units) => JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "add_food_entry",
      "arguments": { 
        "foodId": foodId, 
        "foodEntryName": name + " (Gachas)",
        "servingId": servingId, 
        "numberOfUnits": units,
        "mealType": "breakfast"
      }
    }
  },
  "id": Math.floor(Math.random() * 1000)
});

const GACHAS_ID = "17297090";

// 1. Agregar a la comida guardada
console.log(addItem(GACHAS_ID, "51055285", "Avena", "43281176", 1));
console.log(addItem(GACHAS_ID, "794", "Leche Entera", "1136439", 2.5)); // 250ml

// 2. Agregar al diario de hoy
console.log(logItem("Avena", "51055285", "43281176", 1));
console.log(logItem("Leche Entera", "794", "1136439", 2.5));
