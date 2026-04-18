package exceptionIfazeMethodThrowUncheckedAdd;

import testing_lib.exceptionIfazeMethodThrowUncheckedAdd.ExceptionIfazeMethodThrowUncheckedAdd;

public class Main {

	public static void main(String[] args) {
		ExceptionIfazeMethodThrowUncheckedAdd constr = new ExceptionIfazeMethodThrowUncheckedAdd() {
			@Override public void method1() {}
		};
		constr.method1();
	}
	
}
