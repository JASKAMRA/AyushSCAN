@app.route("/chatbot/message", methods=["POST"])
def chatbot():
    data = request.get_json()
    user_input = data.get("message", "")
    mode = data.get("mode", "price")

    print("User input:", user_input)
    print("Selected mode:", mode)

    if mode == "price":
        price_response = find_medicine_price(user_input)
        print("Medicine Match:", price_response)
        if price_response:
            return jsonify({"reply": price_response})
        return jsonify({"reply": "Sorry, medicine not found in Janaushadhi database."})

    elif mode == "gemini":
        print("Calling Gemini...")
        try:
            model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
            chat = model.start_chat()
            response = chat.send_message(user_input)
            return jsonify({"reply": response.text})
        except Exception as e:
            print("Gemini error:", e)
            return jsonify({"reply": "Gemini failed: " + str(e)})

    return jsonify({"reply": "Invalid mode selected."})


@app.route("/chatbot")
def chatbot_page():
    if "user_id" not in session:
        return redirect("/login")

    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT username, email, first_name, last_name FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

    return render_template("chatbot.html", lang=session.get("language", "english"), user=user)
