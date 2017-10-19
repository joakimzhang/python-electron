// This file is required by the index.html file and will
// be executed in the renderer process for that window.
// All of the Node.js APIs are available in this process.
// renderer.js

const zerorpc = require("zerorpc")
let client = new zerorpc.Client()
client.connect("tcp://127.0.0.1:4243")

let formula = document.querySelector('#formula')
let result = document.querySelector('#result')
formula.addEventListener('input', () => {
  client.invoke("echo", formula.value, (error, res) => {
    if(error) {
      console.error(error)
    } else {
      result.textContent = res
    }
  })
})
document.getElementById("myBtn").addEventListener("click", function(){
    document.getElementById("demo").innerHTML = "Hello World";
});

function myfun(){

document.getElementById("demo").innerHTML = "adsfasdHello World";
//alert("this window.onload"); 　　
}
window.setInterval(function(){
//document.getElementById("demo").innerHTML = "adsfasdHello World";
  client.invoke("rand", (error, res) => {
    if(error) {
      //console.error(error)
      document.getElementById("demo").innerHTML = error;
    } else {
      //result.textContent = res
      document.getElementById("demo").innerHTML = res;
    }
  })
},50);
//window.onload = myfun;

formula.dispatchEvent(new Event('input'))


