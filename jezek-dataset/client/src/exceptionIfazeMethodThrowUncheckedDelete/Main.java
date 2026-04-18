package exceptionIfazeMethodThrowUncheckedDelete;

import testing_lib.exceptionIfazeMethodThrowUncheckedDelete.ExceptionIfazeMethodThrowUncheckedDelete;

public class Main {

	public static void main(String[] args) {
		ExceptionIfazeMethodThrowUncheckedDelete constr = new ExceptionIfazeMethodThrowUncheckedDelete() {
			@Override public void method1() {}
		};
		constr.method1();
	}
	
}
