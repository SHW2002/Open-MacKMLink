"""Local, non-sensitive surface for a real Snipping Tool integration check."""
import tkinter as tk

window = tk.Tk()
window.title("MacKMLink Repair Test Canvas")
window.geometry("640x400+400+240")
canvas = tk.Canvas(window, width=640, height=400, bg="white", highlightthickness=0)
canvas.pack(fill="both", expand=True)
canvas.create_text(320, 65, text="MacKMLink Repair Test", font=("Arial", 24))
for index, color in enumerate(("#e94b35", "#21a366", "#2878cf")):
    x = 100 + index * 160
    canvas.create_rectangle(x, 130, x + 120, 270, fill=color, outline="")
canvas.create_text(320, 330, text="Clipboard bitmap / connection stability", font=("Arial", 16))
window.mainloop()
