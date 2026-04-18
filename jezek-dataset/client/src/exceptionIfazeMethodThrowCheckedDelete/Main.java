package exceptionIfazeMethodThrowCheckedDelete;

import java.io.IOException;

import testing_lib.exceptionIfazeMethodThrowCheckedDelete.ExceptionIfazeMethodThrowCheckedDelete;

public class Main {
	public static void main(String[] args) {
		ExceptionIfazeMethodThrowCheckedDelete constr = new ExceptionIfazeMethodThrowCheckedDelete() {
			@Override public void method1() {}
		};
		try {
			constr.method1();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
}
