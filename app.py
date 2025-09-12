from flask import Flask, render_template, request

app = Flask(__name__)

history = []  # keep history outside so it is not reset each request

@app.route('/', methods=["GET", "POST"])
def calculator():
    result = None

    if request.method == 'POST':
        # get numbers
        a = int(request.form.get("num1"))
        b = int(request.form.get("num2"))
        operation = request.form.get("operation")

        # perform operation
        if operation == "add":
            result = a + b
            history.append(f"{a} + {b} = {result}")
        elif operation == "subtract":
            result = a - b
            history.append(f"{a} - {b} = {result}")
        elif operation == "multiply":
            result = a * b
            history.append(f"{a} * {b} = {result}")
        elif operation == "divide":
            if b != 0:
                result = a / b
                history.append(f"{a} / {b} = {result}")
            else:
                result = "Error: Division by zero"
                history.append(f"{a} / {b} = Error")

    return render_template('calculator.html', result=result, history=history)


if __name__ == '__main__':
    app.run(debug=True)                                                                      
                                                                                           
                     
                 
                 
                 
                        
                 
            
    